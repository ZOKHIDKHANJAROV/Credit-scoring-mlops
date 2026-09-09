from unittest.mock import Mock

from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.schemas.decisions import AgentDecision


client = TestClient(agent_service.app)


def test_agent_to_approval_to_execution_lifecycle(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()

    monkeypatch.setattr(
        agent_service,
        "build_orchestrator",
        lambda: MockOrchestrator(
            AgentDecision(
                action="propose_retraining",
                reason="Model drift exceeded the configured threshold",
                parameters={"confidence": 0.97},
                requires_human_approval=True,
            )
        ),
    )

    executor = Mock()
    executor.apply_training_job.return_value = {
        "executed": True,
        "action": "create_training_job",
        "namespace": "ai-engineering",
        "job_name": "credit-training-test-approval",
        "execution_id": "test-approval",
    }
    monkeypatch.setattr(agent_service, "kubernetes_executor", executor)

    decision_response = client.post(
        "/api/v1/agent/decision",
        json={"task": "Evaluate retraining", "context": {"event_id": "evt-001"}},
    )
    assert decision_response.status_code == 200
    decision_payload = decision_response.json()
    approval_id = decision_payload["approval_id"]
    assert approval_id

    approval_response = client.get(f"/api/v1/approvals/{approval_id}")
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "pending"

    human_response = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={
            "approval_id": approval_id,
            "approved": True,
            "decided_by": "operator",
            "comment": "Approved after drift review",
        },
    )
    assert human_response.status_code == 200
    assert human_response.json()["status"] == "approved"

    execution_response = client.post(f"/api/v1/approvals/{approval_id}/execute")
    assert execution_response.status_code == 200
    assert execution_response.json()["status"] == "completed"
    executor.apply_training_job.assert_called_once_with(
        approved=True,
        execution_id=approval_id,
    )

    trace_response = client.get(f"/api/v1/audit/traces/{approval_id}")
    assert trace_response.status_code == 200
    event_types = [event["event_type"] for event in trace_response.json()]
    assert event_types == [
        "approval_requested",
        "approval_decided",
        "execution_started",
        "execution_completed",
    ]


class MockOrchestrator:
    def __init__(self, decision: AgentDecision):
        self.decision = decision

    def reason(self, task: str, context: dict) -> AgentDecision:
        return self.decision
