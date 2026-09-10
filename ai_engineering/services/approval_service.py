"""Human-in-the-loop service for approval-gated engineering actions."""

from __future__ import annotations

from typing import Protocol, Any

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.tools.kubernetes_executor import KubernetesExecutionUnknown


class TrainingJobExecutor(Protocol):
    def apply_training_job(self, approved: bool, execution_id: str | None = None) -> dict[str, Any]: ...


class ApprovalService:
    """Coordinate approval state and execution without letting the LLM bypass approval."""

    def __init__(self, store: ApprovalStore, executor: TrainingJobExecutor) -> None:
        self.store = store
        self.executor = executor

    def create_training_approval(self, reason: str, execution_plan: dict[str, Any]) -> ApprovalRequest:
        request = ApprovalRequest(action="create_training_job", reason=reason, execution_plan=execution_plan)
        return self.store.create(request)

    def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        return self.store.decide(decision)

    def execute(self, approval_id: str) -> ApprovalRequest:
        request, owns_execution = self.store.claim_execution(approval_id)
        if not owns_execution:
            return request
        try:
            result = self.executor.apply_training_job(approved=True, execution_id=approval_id)
        except KubernetesExecutionUnknown as exc:
            return self.store.mark_unknown(approval_id, {"executed": False, "unknown": True, "error": str(exc)})
        except Exception as exc:
            return self.store.mark_failed(approval_id, {"executed": False, "action": request.action, "reason": "Training job execution failed", "error": str(exc)})
        if not result.get("executed", False):
            return self.store.mark_failed(approval_id, result)
        return self.store.mark_completed(approval_id, result)
