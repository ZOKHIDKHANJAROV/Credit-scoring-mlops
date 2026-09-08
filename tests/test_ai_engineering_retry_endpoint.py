from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus


client = TestClient(agent_service.app)


def make_unknown() -> ApprovalRequest:
    request = agent_service.approval_store.create(
        ApprovalRequest(action="create_training_job", reason="retry endpoint test")
    )
    agent_service.approval_store.decide(
        ApprovalDecision(
            approval_id=request.approval_id,
            approved=True,
            decided_by="test",
        )
    )
    agent_service.approval_store.mark_executing(request.approval_id)
    return agent_service.approval_store.mark_unknown(
        request.approval_id,
        {"unknown": True},
    )


def test_retry_endpoint_reexecutes_only_after_job_absence(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()

    monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "get_training_job_status",
        lambda job_name: {"exists": False, "status": "absent", "job_name": job_name},
    )
    apply = monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "apply_training_job",
        lambda approved, execution_id: {
            "executed": True,
            "execution_id": execution_id,
        },
    )

    response = client.post(f"/api/v1/approvals/{request.approval_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == ApprovalStatus.COMPLETED.value
    assert response.json()["approval_id"] == request.approval_id
    assert apply is None

    events = client.get(f"/api/v1/audit/traces/{request.approval_id}")
    assert events.status_code == 200
    assert any(event["event_type"] == "execution_retry" for event in events.json())


def test_retry_endpoint_does_not_retry_when_job_exists(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    request = make_unknown()
    apply_calls = []

    monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "get_training_job_status",
        lambda job_name: {"exists": True, "status": "running", "job_name": job_name},
    )
    monkeypatch.setattr(
        agent_service.kubernetes_executor,
        "apply_training_job",
        lambda **kwargs: apply_calls.append(kwargs),
    )

    response = client.post(f"/api/v1/approvals/{request.approval_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == ApprovalStatus.UNKNOWN.value
    assert apply_calls == []
