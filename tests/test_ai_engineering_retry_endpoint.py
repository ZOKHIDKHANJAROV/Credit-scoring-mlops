from unittest.mock import Mock

from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus
from ai_engineering.storage.approval_store import InvalidApprovalTransition


client = TestClient(agent_service.app)


def make_unknown() -> ApprovalRequest:
    request = agent_service.approval_store.create(
        ApprovalRequest(action="create_training_job", reason="retry endpoint test")
    )
    agent_service.approval_store.decide(
        ApprovalDecision(approval_id=request.approval_id, approved=True, decided_by="test")
    )
    agent_service.approval_store.mark_executing(request.approval_id)
    return agent_service.approval_store.mark_unknown(request.approval_id, {"unknown": True})


def test_retry_endpoint_reexecutes_only_after_job_absence(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()
    apply = Mock(return_value={"executed": True, "execution_id": request.approval_id})

    monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "get_training_job_status",
        Mock(return_value={"exists": False, "status": "absent", "job_name": f"credit-training-{request.approval_id}"}),
    )
    monkeypatch.setattr(agent_service.kubernetes_executor, "apply_training_job", apply)

    response = client.post(f"/api/v1/approvals/{request.approval_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == ApprovalStatus.COMPLETED.value
    assert response.json()["approval_id"] == request.approval_id
    apply.assert_called_once_with(approved=True, execution_id=request.approval_id)

    events = client.get(f"/api/v1/audit/traces/{request.approval_id}")
    assert events.status_code == 200
    assert any(event["event_type"] == "execution_retry" for event in events.json())


def test_retry_endpoint_does_not_retry_when_job_exists(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()
    apply = Mock()

    monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "get_training_job_status",
        Mock(return_value={"exists": True, "status": "running", "job_name": f"credit-training-{request.approval_id}"}),
    )
    monkeypatch.setattr(agent_service.kubernetes_executor, "apply_training_job", apply)

    response = client.post(f"/api/v1/approvals/{request.approval_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == ApprovalStatus.UNKNOWN.value
    apply.assert_not_called()


def test_retry_endpoint_reconciles_when_job_already_exists_and_completed(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()
    apply = Mock()

    monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "get_training_job_status",
        Mock(return_value={"exists": True, "status": "completed", "job_name": f"credit-training-{request.approval_id}"}),
    )
    monkeypatch.setattr(agent_service.kubernetes_executor, "apply_training_job", apply)

    response = client.post(f"/api/v1/approvals/{request.approval_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == ApprovalStatus.COMPLETED.value
    apply.assert_not_called()


def test_retry_endpoint_returns_404_for_unknown_approval() -> None:
    agent_service.approval_store.clear()
    response = client.post("/api/v1/approvals/00000000-0000-0000-0000-000000000000/retry")
    assert response.status_code == 404


def test_retry_endpoint_handles_race_for_unknown_state(monkeypatch) -> None:
    """A losing concurrent retry must not become a 500 or execute twice."""
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()

    status = Mock(
        return_value={
            "exists": False,
            "status": "absent",
            "job_name": f"credit-training-{request.approval_id}",
        }
    )
    apply = Mock(return_value={"executed": True, "execution_id": request.approval_id})
    monkeypatch.setattr(agent_service.kubernetes_executor, "get_training_job_status", status)
    monkeypatch.setattr(agent_service.kubernetes_executor, "apply_training_job", apply)

    original_mark_retry = agent_service.approval_store.mark_retry_executing
    calls = 0

    def race_once(approval_id: str, request=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_mark_retry(approval_id, request)
        raise InvalidApprovalTransition("Retry execution requires unknown state, got executing")

    monkeypatch.setattr(agent_service.approval_store, "mark_retry_executing", race_once)

    first = client.post(f"/api/v1/approvals/{request.approval_id}/retry")
    second = client.post(f"/api/v1/approvals/{request.approval_id}/retry")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == ApprovalStatus.COMPLETED.value
    assert second.json()["status"] == ApprovalStatus.COMPLETED.value
    apply.assert_called_once_with(approved=True, execution_id=request.approval_id)
