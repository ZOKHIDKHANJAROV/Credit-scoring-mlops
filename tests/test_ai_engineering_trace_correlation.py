from unittest.mock import Mock

from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.schemas.decisions import AgentDecision


client = TestClient(agent_service.app)


class MockOrchestrator:
    def reason(self, task: str, context: dict) -> AgentDecision:
        return AgentDecision(
            action="propose_retraining",
            reason="Trace correlation regression test",
            parameters={"confidence": 0.99},
            requires_human_approval=True,
        )


def test_decision_approval_execution_share_trace_id(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()
    monkeypatch.setattr(agent_service, "build_orchestrator", lambda: MockOrchestrator())

    executor = Mock()
    executor.apply_training_job.return_value = {
        "executed": True,
        "action": "create_training_job",
        "namespace": "ai-engineering",
        "job_name": "credit-training-trace-test",
        "execution_id": "trace-test",
    }
    monkeypatch.setattr(agent_service, "kubernetes_executor", executor)

    trace_id = "trace-20260909-001"
    decision = client.post(
        "/api/v1/agent/decision",
        json={"task": "Evaluate retraining", "context": {"trace_id": trace_id}},
    )
    assert decision.status_code == 200
    payload = decision.json()
    approval_id = payload["approval_id"]
    assert payload["trace_id"] == trace_id

    approval = client.get(f"/api/v1/approvals/{approval_id}")
    assert approval.status_code == 200
    assert approval.json()["trace_id"] == trace_id

    approved = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={
            "approval_id": approval_id,
            "approved": True,
            "decided_by": "operator",
        },
    )
    assert approved.status_code == 200

    executed = client.post(f"/api/v1/approvals/{approval_id}/execute")
    assert executed.status_code == 200
    assert executed.json()["trace_id"] == trace_id

    trace = client.get(f"/api/v1/audit/traces/{trace_id}")
    assert trace.status_code == 200
    event_types = [event["event_type"] for event in trace.json()]
    assert event_types == [
        "decision_created",
        "approval_requested",
        "approval_decided",
        "execution_started",
        "execution_completed",
    ]


def test_direct_approval_gets_own_trace_id() -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()

    response = client.post(
        "/api/v1/approvals",
        json={
            "action": "create_training_job",
            "reason": "Direct approval trace test",
            "execution_plan": {},
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["trace_id"]
    assert payload["trace_id"] != payload["approval_id"]

    trace = client.get(f"/api/v1/audit/traces/{payload['trace_id']}")
    assert trace.status_code == 200
    assert len(trace.json()) == 1
    assert trace.json()[0]["event_type"] == "approval_requested"
