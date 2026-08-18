"""Approval-gated workflow for promoting an evaluated model in MLflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_engineering.tools.mlflow_tools import MLflowTools


@dataclass(frozen=True)
class PromotionResult:
    """Outcome of a guarded model promotion attempt."""

    status: str
    reason: str
    details: dict[str, Any]


class ModelPromotionWorkflow:
    """Promote a candidate only when evaluation and human approval both allow it."""

    def __init__(self, mlflow_tools: MLflowTools | None = None) -> None:
        self.mlflow_tools = mlflow_tools or MLflowTools()

    def execute(
        self,
        candidate_version: str,
        evaluation: dict[str, Any],
        human_approved: bool,
    ) -> PromotionResult:
        """Apply the promotion gate and delegate the final alias update to MLflowTools."""
        decision = evaluation.get("decision")

        if decision == "MANUAL_REVIEW":
            return PromotionResult(
                status="manual_review",
                reason="Model evaluation requires manual review",
                details={"decision": decision},
            )

        if decision == "REJECT":
            return PromotionResult(
                status="rejected",
                reason="Model evaluation rejected the candidate",
                details={"decision": decision},
            )

        if decision != "PROMOTE" or evaluation.get("approved") is not True:
            return PromotionResult(
                status="rejected",
                reason="Candidate does not have a valid PROMOTE evaluation",
                details={"decision": decision, "approved": evaluation.get("approved")},
            )

        if not human_approved:
            return PromotionResult(
                status="approval_required",
                reason="Human approval is required before promotion",
                details={"decision": decision},
            )

        result = self.mlflow_tools.promote_model(
            candidate_version=candidate_version,
            decision=decision,
            human_approved=human_approved,
        )

        if result.get("promoted"):
            return PromotionResult(
                status="promoted",
                reason="Candidate model promoted to champion",
                details=result,
            )

        if result.get("already_champion"):
            return PromotionResult(
                status="already_champion",
                reason=result["reason"],
                details=result,
            )

        return PromotionResult(
            status="failed",
            reason=result.get("reason", "Model promotion failed"),
            details=result,
        )
