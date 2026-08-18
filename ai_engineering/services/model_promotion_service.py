"""Human-in-the-loop service for model promotion approvals."""

from __future__ import annotations

from typing import Any

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.workflows.model_promotion_workflow import ModelPromotionWorkflow


class ModelPromotionApprovalService:
    """Create, decide and execute model-promotion approvals."""

    ACTION = "promote_model"

    def __init__(
        self,
        store: ApprovalStore,
        workflow: ModelPromotionWorkflow,
    ) -> None:
        self.store = store
        self.workflow = workflow

    def create(
        self,
        candidate_version: str,
        evaluation: dict[str, Any],
        reason: str,
    ) -> ApprovalRequest:
        if not candidate_version.strip():
            raise ValueError("candidate_version must not be empty")
        if evaluation.get("decision") != "PROMOTE" or evaluation.get("approved") is not True:
            raise ValueError("Only an approved PROMOTE evaluation can create a promotion request")

        return self.store.create(
            ApprovalRequest(
                action=self.ACTION,
                reason=reason,
                execution_plan={
                    "candidate_version": candidate_version,
                    "evaluation": evaluation,
                },
            )
        )

    def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        return self.store.decide(decision)

    def execute(self, approval_id: str) -> ApprovalRequest:
        request = self.store.mark_executing(approval_id)
        if request.action != self.ACTION:
            return self.store.mark_failed(
                approval_id,
                {
                    "executed": False,
                    "reason": f"Unsupported approval action: {request.action}",
                },
            )

        plan = request.execution_plan
        result = self.workflow.execute(
            candidate_version=str(plan.get("candidate_version", "")),
            evaluation=plan.get("evaluation", {}),
            human_approved=True,
        )

        payload = {
            "executed": result.status == "promoted",
            "status": result.status,
            "reason": result.reason,
            "details": result.details,
        }

        if result.status in {"promoted", "already_champion"}:
            return self.store.mark_completed(approval_id, payload)
        return self.store.mark_failed(approval_id, payload)
