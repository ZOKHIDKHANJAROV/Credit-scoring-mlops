from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_engineering.api import agent_service
from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus
from ai_engineering.storage.approval_store import ApprovalRequestRow


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
    assert response.json()["status"] == ApprovalStatus.EXECUTING.value
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


def test_retry_endpoint_second_caller_cannot_claim_executing_retry(monkeypatch) -> None:
    """Once claimed, a concurrent retry cannot reach the Kubernetes create path."""
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

    claimed, owns_retry = agent_service.approval_store.claim_retry_execution(request.approval_id)
    assert owns_retry is True
    assert claimed.status == ApprovalStatus.EXECUTING

    response = client.post(f"/api/v1/approvals/{request.approval_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == ApprovalStatus.EXECUTING.value
    apply.assert_not_called()


def test_reconcile_can_finish_claimed_running_retry(monkeypatch) -> None:
    """A running Job remains recoverable after retry ownership moves to EXECUTING."""
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()
    agent_service.approval_store.claim_retry_execution(request.approval_id)

    status = Mock(
        side_effect=[
            {"exists": True, "status": "running", "job_name": f"credit-training-{request.approval_id}"},
            {"exists": True, "status": "completed", "job_name": f"credit-training-{request.approval_id}"},
        ]
    )
    monkeypatch.setattr(agent_service.kubernetes_executor, "get_training_job_status", status)

    running = client.post(f"/api/v1/approvals/{request.approval_id}/reconcile")
    assert running.status_code == 200
    assert running.json()["status"] == ApprovalStatus.EXECUTING.value

    completed = client.post(f"/api/v1/approvals/{request.approval_id}/reconcile")
    assert completed.status_code == 200
    assert completed.json()["status"] == ApprovalStatus.COMPLETED.value
    assert status.call_count == 2


def test_reconcile_does_not_recover_fresh_execution_without_job(monkeypatch) -> None:
    """A recently claimed execution gets a grace period before stale recovery."""
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()
    claimed, owner = agent_service.approval_store.claim_retry_execution(request.approval_id)
    assert owner is True
    assert claimed.execution_started_at is not None

    monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "get_training_job_status",
        Mock(return_value={"exists": False, "status": "absent", "job_name": f"credit-training-{request.approval_id}"}),
    )

    response = client.post(f"/api/v1/approvals/{request.approval_id}/reconcile")

    assert response.status_code == 200
    assert response.json()["status"] == ApprovalStatus.EXECUTING.value


def test_reconcile_recovers_stale_execution_without_job(monkeypatch) -> None:
    """An abandoned execution lease becomes UNKNOWN and can be retried safely."""
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()
    claimed, owner = agent_service.approval_store.claim_retry_execution(request.approval_id)
    assert owner is True
    assert claimed.execution_started_at is not None

    with Session(agent_service.approval_store.engine) as session:
        row = session.scalar(
            select(ApprovalRequestRow).where(ApprovalRequestRow.approval_id == request.approval_id)
        )
        assert row is not None
        row.execution_started_at = datetime.now(timezone.utc) - timedelta(seconds=3600)
        session.commit()

    monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "get_training_job_status",
        Mock(return_value={"exists": False, "status": "absent", "job_name": f"credit-training-{request.approval_id}"}),
    )

    response = client.post(f"/api/v1/approvals/{request.approval_id}/reconcile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == ApprovalStatus.UNKNOWN.value
    assert payload["execution_result"]["recovered_stale_execution"] is True
    assert payload["execution_result"]["unknown"] is True

    events = client.get(f"/api/v1/audit/traces/{request.approval_id}")
    assert events.status_code == 200
    assert any(event["event_type"] == "execution_unknown" for event in events.json())
