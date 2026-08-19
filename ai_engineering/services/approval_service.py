"""Human-in-the-loop service for approval-gated engineering actions."""

from __future__ import annotations

from typing import Protocol, Any

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest
from ai_engineering.storage.approval_store import ApprovalStore


class TrainingJobExecutor(Protocol):
    """Protocol implemented by the Kubernetes execution adapter."""

    def apply_training_job(self, approved: bool) -> dict[str, Any]:
        """Execute the approved training job."""
        ...


class ApprovalService:
    """Coordinate approval state and execution without letting the LLM bypass approval."""

    def __init__(self, store: ApprovalStore, executor: TrainingJobExecutor) -> None:
        self.store = store
        self.executor = executor

    def create_training_approval(
        self,
        reason: str,
        execution_plan: dict[str, Any],
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            action="create_training_job",
            reason=reason,
            execution_plan=execution_plan,
        )
        return self.store.create(request)

    def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        return self.store.decide(decision)

    def execute(self, approval_id: str) -> ApprovalRequest:
        request = self.store.mark_executing(approval_id)

        try:
            result = self.executor.apply_training_job(approved=True)
        except Exception as exc:
            return self.store.mark_failed(
                approval_id,
                {
                    "executed": False,
                    "action": request.action,
                    "reason": "Training job execution failed",
                    "error": str(exc),
                },
            )

        if not result.get("executed", False):
            return self.store.mark_failed(approval_id, result)

        return self.store.mark_completed(approval_id, result)
