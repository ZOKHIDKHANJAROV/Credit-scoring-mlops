from unittest.mock import Mock

from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.schemas.decisions import AgentDecision
from ai_engineering.tools.kubernetes_executor import KubernetesExecutionUnknown


client = TestClient(agent_service.app)


def test_full_lifecycle_reconcile_and_command_center(monkeypatch) -> None:
    """Exercise decision -> approval -> unknown execution -> reconciliation -> dashboard."""

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
    executor.apply_training_job.side_effect = KubernetesExecutionUnknown(
        "Kubernetes API response was unavailable after submission"
    )
    executor.get_training_job_status.return_value = {
        "exists": True,
        "status": "completed",
        "job_name": "credit-training-test",
    }
    monkeypatch.setattr(agent_service, "kubernetes_executor", executor)
    monkeypatch.setattr(
        agent_service,
        "reconciliation_service",
        agent_service.ReconciliationService(
            agent_service.approval_store,
            executor,
            agent_service.audit_service,
        ),
    )

    decision_response = client.post(
        "/api/v1/agent/decision",
        json={
            "task": "Evaluate retraining",
            "context": {"event_id": "evt-full-lifecycle"},
        },
    )
    assert decision_response.status_code == 200
    decision_payload = decision_response.json()
    approval_id = decision_payload["approval_id"]
    trace_id = decision_payload["trace_id"]

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
    assert execution_response.json()["status"] == "unknown"
    executor.apply_training_job.assert_called_once_with(
        approved=True,
        execution_id=approval_id,
    )

    reconcilable_response = client.get("/api/v1/command-center/overview")
    assert reconcilable_response.status_code == 200
    reconcilable_payload = reconcilable_response.json()
    assert reconcilable_payload["approval_counts"]["unknown"] == 1
    assert any(
        item["approval_id"] == approval_id
        for item in reconcilable_payload["reconcilable_approvals"]
    )

    reconcile_response = client.post(f"/api/v1/approvals/{approval_id}/reconcile")
    assert reconcile_response.status_code == 200
    assert reconcile_response.json()["status"] == "completed"
    executor.get_training_job_status.assert_called_once_with(
        f"credit-training-{approval_id}"
    )

    final_overview = client.get("/api/v1/command-center/overview")
    assert final_overview.status_code == 200
    overview = final_overview.json()
    assert overview["approval_counts"]["completed"] == 1
    assert not overview["reconcilable_approvals"]
    assert overview["recent_approvals"][0]["approval_id"] == approval_id
    assert overview["recent_approvals"][0]["status"] == "completed"
    assert overview["audit_event_counts"]["execution_unknown"] == 1
    assert overview["audit_event_counts"]["execution_reconciliation_started"] == 1
    assert overview["audit_event_counts"]["execution_reconciliation_completed"] == 1

    trace_response = client.get(f"/api/v1/audit/traces/{trace_id}")
    assert trace_response.status_code == 200
    event_types = [event["event_type"] for event in trace_response.json()]
    assert event_types == [
        "decision_created",
        "approval_requested",
        "approval_decided",
        "execution_started",
        "execution_unknown",
        "execution_reconciliation_started",
        "execution_reconciliation_completed",
    ]


class MockOrchestrator:
    def __init__(self, decision: AgentDecision):
        self.decision = decision

    def reason(self, task: str, context: dict) -> AgentDecision:
        return self.decision
