"""Human-in-the-loop service for approval-gated engineering actions."""

from __future__ import annotations

from typing import Any, Protocol

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest
from ai_engineering.storage.approval_store import ApprovalStore


class TrainingJobExecutor(Protocol):
    """Protocol implemented by the Kubernetes execution adapter."""

    def apply_training_job(self, approved: bool) -> dict[str, Any]:
        """Create the approved training job."""
        ...

    def get_training_job_status(self, job_name: str) -> dict[str, Any]:
        """Read the current status of a training job."""
        ...


class ApprovalService:
    """Coordinate approval state and Kubernetes execution."""

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
        """Create the approved Job and leave it in executing state until polled."""
        request = self.store.mark_executing(approval_id)
        job_name = str(request.execution_plan.get("job_name", "credit-model-training"))

        try:
            result = self.executor.apply_training_job(approved=True)
        except Exception as exc:
            return self.store.mark_failed(approval_id, self._failure_result(request, exc))

        if not result.get("executed", False):
            return self.store.mark_failed(approval_id, result)

        result = {**result, "job_name": job_name, "lifecycle": "running"}
        return self.store.update_execution_result(approval_id, result)

    def refresh_execution(self, approval_id: str) -> ApprovalRequest:
        """Poll a running training Job and transition it when Kubernetes finishes."""
        request = self.store.get(approval_id)
        if request is None:
            raise KeyError(f"Approval not found: {approval_id}")
        if request.status.value != "executing":
            raise ValueError(
                f"Only executing requests can be refreshed; current status is {request.status.value}"
            )

        job_name = str(request.execution_plan.get("job_name", "credit-model-training"))
        try:
            result = self.executor.get_training_job_status(job_name)
        except Exception as exc:
            return self.store.mark_failed(approval_id, self._failure_result(request, exc))

        lifecycle = result.get("lifecycle", "unknown")
        if lifecycle == "completed":
            return self.store.mark_completed(approval_id, result)
        if lifecycle == "failed":
            return self.store.mark_failed(approval_id, result)

        result = {**result, "job_name": job_name, "lifecycle": lifecycle}
        return self.store.update_execution_result(approval_id, result)

    @staticmethod
    def _failure_result(request: ApprovalRequest, exc: Exception) -> dict[str, Any]:
        return {
            "executed": False,
            "action": request.action,
            "reason": "Training job execution failed",
            "error": str(exc),
            "lifecycle": "failed",
        }
