from dataclasses import dataclass

from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.schemas.decisions import AgentDecision


client = TestClient(agent_service.app)


@dataclass
class FakeOrchestrator:
    decision: AgentDecision

    def reason(self, task: str, context: dict) -> AgentDecision:
        return self.decision


def test_agent_decision_creates_approval_for_retraining(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()

    monkeypatch.setattr(
        agent_service,
        "build_orchestrator",
        lambda: FakeOrchestrator(
            AgentDecision(
                action="propose_retraining",
                reason="Drift threshold exceeded",
                parameters={"confidence": 0.91, "tools_used": ["monitoring_get_retrain_signal"]},
                requires_human_approval=True,
            )
        ),
    )

    response = client.post(
        "/api/v1/agent/decision",
        json={"task": "Evaluate whether retraining is needed", "context": {"event_id": "evt-123"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "propose_retraining"
    assert payload["requires_human_approval"] is True
    assert payload["approval_id"]

    approval = client.get(f"/api/v1/approvals/{payload['approval_id']}")
    assert approval.status_code == 200
    assert approval.json()["action"] == "create_training_job"
    assert approval.json()["status"] == "pending"

    events = client.get(f"/api/v1/audit/traces/{payload['approval_id']}")
    assert events.status_code == 200
    assert events.json()[0]["event_type"] == "approval_requested"


def test_agent_decision_does_not_create_approval_for_read_only_action(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()

    monkeypatch.setattr(
        agent_service,
        "build_orchestrator",
        lambda: FakeOrchestrator(
            AgentDecision(
                action="investigate",
                reason="Inspect current model and monitoring state",
                parameters={"confidence": 0.88},
                requires_human_approval=False,
            )
        ),
    )

    response = client.post(
        "/api/v1/agent/decision",
        json={"task": "Inspect the current model", "context": {"trace_id": "trace-456"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "investigate"
    assert payload["approval_id"] is None
    assert payload["trace_id"] == "trace-456"
    assert client.get("/api/v1/approvals").json() == []


def test_agent_decision_endpoint_does_not_turn_manual_review_into_mutation(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()

    monkeypatch.setattr(
        agent_service,
        "build_orchestrator",
        lambda: FakeOrchestrator(
            AgentDecision(
                action="manual_review",
                reason="LLM output is outside the allowlist",
                parameters={},
                requires_human_approval=True,
            )
        ),
    )

    response = client.post(
        "/api/v1/agent/decision",
        json={"task": "Perform an unsupported operation", "context": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "manual_review"
    assert payload["approval_id"] is None
    assert client.get("/api/v1/approvals").json() == []
