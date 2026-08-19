"""ML evaluation agent for safe model promotion analysis."""

from __future__ import annotations

from typing import Any

from ai_engineering.agents.reviewer_agent import ReviewerAgent
from ai_engineering.tools.mlflow_tools import MLflowTools


class MLAgent:
    """Inspect MLflow state and produce a deterministic promotion recommendation."""

    def __init__(
        self,
        tools: MLflowTools | None = None,
        reviewer: ReviewerAgent | None = None,
    ) -> None:
        self.tools = tools or MLflowTools()
        self.reviewer = reviewer or ReviewerAgent()

    def inspect(self) -> dict[str, Any]:
        """Return champion metadata and latest model comparison."""
        return {
            "champion": self.tools.get_champion_model(),
            "model_comparison": self.tools.compare_latest_models(),
        }

    def evaluate(self) -> dict[str, Any]:
        """Evaluate the strongest latest candidate against the champion.

        This method is read-only. It never changes an MLflow alias or deploys a
        model. Any promotion decision remains subject to the approval workflow.
        """
        state = self.inspect()
        champion_metadata = state["champion"]
        candidates = state["model_comparison"]

        if not candidates:
            return {
                "decision": "MANUAL_REVIEW",
                "reason": "No comparable model runs are available",
                "requires_human_approval": True,
                "champion": champion_metadata,
                "candidate": None,
            }

        candidate = candidates[0]
        candidate_run_id = candidate.get("run_id")
        candidate_metrics = self.tools.get_run_metrics(candidate_run_id)

        if not candidate_metrics.get("available"):
            return {
                "decision": "MANUAL_REVIEW",
                "reason": "Candidate metrics could not be retrieved from MLflow",
                "requires_human_approval": True,
                "champion": champion_metadata,
                "candidate": candidate,
                "candidate_metrics": candidate_metrics,
            }

        champion_run_id = champion_metadata.get("run_id") if champion_metadata.get("available") else None
        champion_metrics = (
            self.tools.get_run_metrics(champion_run_id)
            if champion_run_id
            else {"available": False, "reason": "Champion run metadata is unavailable"}
        )

        if not champion_metrics.get("available"):
            return {
                "decision": "MANUAL_REVIEW",
                "reason": "Champion metrics could not be retrieved from MLflow",
                "requires_human_approval": True,
                "champion": champion_metadata,
                "champion_metrics": champion_metrics,
                "candidate": candidate,
                "candidate_metrics": candidate_metrics,
            }

        review = self.reviewer.review(
            champion=champion_metrics["metrics"],
            candidate=candidate_metrics["metrics"],
        )

        return {
            "decision": review["decision"],
            "reason": review["reason"],
            "requires_human_approval": True,
            "champion": {
                **champion_metadata,
                "metrics": champion_metrics["metrics"],
            },
            "candidate": {
                **candidate,
                "metrics": candidate_metrics["metrics"],
            },
            "quality_review": review,
        }

    def recommend(self) -> dict[str, Any]:
        """Backward-compatible alias for the explicit evaluation workflow."""
        return self.evaluate()
