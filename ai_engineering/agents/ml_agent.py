"""ML agent for safe inspection of model state."""

from __future__ import annotations

from ai_engineering.tools.mlflow_tools import MLflowTools


class MLAgent:
    """Analyze model state without performing mutating MLflow operations."""

    def __init__(self, tools: MLflowTools | None = None) -> None:
        self.tools = tools or MLflowTools()

    def inspect(self) -> dict:
        """Return champion metadata and latest model comparison."""
        return {
            "champion": self.tools.get_champion_model(),
            "model_comparison": self.tools.compare_latest_models(),
        }

    def recommend(self) -> dict:
        """Recommend whether a candidate model should be investigated further."""
        state = self.inspect()
        comparison = state["model_comparison"]

        if not comparison:
            return {
                "action": "manual_review",
                "reason": "No comparable model runs are available",
                "requires_human_approval": True,
            }

        best = comparison[0]
        champion = state["champion"]

        return {
            "action": "evaluate_candidate",
            "reason": (
                f"Best latest model is {best['run_name']} with "
                f"ROC-AUC={best['roc_auc']}. Champion metadata: {champion}."
            ),
            "candidate": best,
            "requires_human_approval": True,
        }
