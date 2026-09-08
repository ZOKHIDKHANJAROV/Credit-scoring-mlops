from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.schemas.decisions import AgentDecision


client = TestClient(agent_service.app)


def test_decision_endpoint_creates_approval_for_retraining(monkeypatch):
    agent_service.audit_store.clear()
    monkeypatch.setattr(
        agent_service,
        "build_orchestrator",
        lambda: _FakeOrchestrator(
            AgentDecision(
                action="propose_retraining",
                reason="Drift threshold exceeded",
                parameters={"confidence": 0.93},
                requires_human_approval=True,
            )
        ),
    )

    response = client.post(
        "/api/v1/agent/decision",
        json={"task": "Evaluate retraining", "context": {"drift": 0.42}},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["action"] == "create_training_job"
    assert payload["execution_plan"]["confidence"] == 0.93
    assert payload["execution_plan"]["source_action"] == "propose_retraining"

    events = client.get(f"/api/v1/audit/traces/{payload['approval_id']}")
    assert events.status_code == 200
    assert [event["event_type"] for event in events.json()] == [
        "decision_created",
        "approval_requested",
    ]


def test_decision_endpoint_does_not_create_approval_for_read_only_decision(monkeypatch):
    agent_service.audit_store.clear()
    monkeypatch.setattr(
        agent_service,
        "build_orchestrator",
        lambda: _FakeOrchestrator(
            AgentDecision(
                action="investigate",
                reason="More evidence is required",
                parameters={"confidence": 0.71},
                requires_human_approval=False,
            )
        ),
    )

    response = client.post(
        "/api/v1/agent/decision",
        json={"task": "Investigate drift", "context": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "investigate"
    assert payload["approval"] is None

    stats = client.get("/api/v1/audit/stats")
    assert stats.json()["event_count"] == 1


def test_decision_endpoint_fails_closed_on_invalid_llm_decision(monkeypatch):
    agent_service.audit_store.clear()
    monkeypatch.setattr(
        agent_service,
        "build_orchestrator",
        lambda: _FakeOrchestrator(
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
        json={"task": "Do something unsafe", "context": {}},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["approval"]["action"] == "manual_review"


class _FakeOrchestrator:
    def __init__(self, decision: AgentDecision):
        self.decision = decision

    def reason(self, task: str, context: dict | None = None) -> AgentDecision:
        return self.decision
