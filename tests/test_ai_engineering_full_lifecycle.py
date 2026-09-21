from unittest.mock import Mock

from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.schemas.approvals import ApprovalStatus
from ai_engineering.schemas.decisions import AgentDecision
from ai_engineering.services.reconciliation_service import ReconciliationService
from ai_engineering.tools.kubernetes_executor import KubernetesExecutionUnknown


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
        "decision_created",
        "approval_requested",
        "approval_decided",
        "execution_started",
        "execution_completed",
    ]


def test_full_reconciliation_lifecycle_updates_overview_and_audit(monkeypatch) -> None:
    agent_service.approval_store.clear()
    agent_service.audit_store.clear()

    monkeypatch.setattr(
        agent_service,
        "build_orchestrator",
        lambda: MockOrchestrator(
            AgentDecision(
                action="propose_retraining",
                reason="Retraining signal requires a controlled training job",
                parameters={"confidence": 0.99},
                requires_human_approval=True,
            )
        ),
    )

    executor = Mock()
    executor.apply_training_job.side_effect = KubernetesExecutionUnknown(
        "Kubernetes API response was lost after Job submission"
    )
    executor.get_training_job_status.return_value = {
        "exists": True,
        "status": "completed",
        "job_name": "credit-training-reconciliation-test",
    }
    monkeypatch.setattr(agent_service, "kubernetes_executor", executor)
    monkeypatch.setattr(
        agent_service,
        "reconciliation_service",
        ReconciliationService(
            agent_service.approval_store,
            executor,
            agent_service.audit_service,
            execution_lease_seconds=1,
        ),
    )

    decision_response = client.post(
        "/api/v1/agent/decision",
        json={"task": "Evaluate retraining", "context": {"event_id": "evt-reconcile-001"}},
    )
    assert decision_response.status_code == 200
    approval_id = decision_response.json()["approval_id"]
    assert approval_id

    human_response = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={
            "approval_id": approval_id,
            "approved": True,
            "decided_by": "operator",
            "comment": "Approved for reconciliation lifecycle test",
        },
    )
    assert human_response.status_code == 200
    assert human_response.json()["status"] == ApprovalStatus.APPROVED.value

    execution_response = client.post(f"/api/v1/approvals/{approval_id}/execute")
    assert execution_response.status_code == 200
    assert execution_response.json()["status"] == ApprovalStatus.UNKNOWN.value

    overview_unknown = client.get("/api/v1/command-center/overview")
    assert overview_unknown.status_code == 200
    unknown_payload = overview_unknown.json()
    assert unknown_payload["approval_counts"][ApprovalStatus.UNKNOWN.value] == 1
    assert any(
        approval["approval_id"] == approval_id
        and approval["status"] == ApprovalStatus.UNKNOWN.value
        for approval in unknown_payload["reconcilable_approvals"]
    )

    reconcile_response = client.post(f"/api/v1/approvals/{approval_id}/reconcile")
    assert reconcile_response.status_code == 200
    assert reconcile_response.json()["status"] == ApprovalStatus.COMPLETED.value
    executor.get_training_job_status.assert_called_once_with(
        f"credit-training-{approval_id}"
    )

    overview_completed = client.get("/api/v1/command-center/overview")
    assert overview_completed.status_code == 200
    completed_payload = overview_completed.json()
    assert completed_payload["approval_counts"][ApprovalStatus.COMPLETED.value] == 1
    assert not any(
        approval["approval_id"] == approval_id
        for approval in completed_payload["reconcilable_approvals"]
    )

    trace_response = client.get(f"/api/v1/audit/traces/{approval_id}")
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
