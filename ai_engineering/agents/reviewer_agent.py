"""Deterministic model quality reviewer for promotion decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QualityGateConfig:
    """Explicit quality gates used before a model can be promoted."""

    min_roc_auc: float = 0.80
    min_recall: float = 0.60
    min_precision: float = 0.50
    min_roc_auc_improvement: float = 0.0


class ReviewerAgent:
    """Evaluate a candidate model against explicit quality gates."""

    def __init__(self, config: QualityGateConfig | None = None) -> None:
        self.config = config or QualityGateConfig()

    def review(
        self,
        champion: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a deterministic promotion decision without changing MLflow."""
        champion_auc = champion.get("roc_auc")
        candidate_auc = candidate.get("roc_auc")
        candidate_recall = candidate.get("recall")
        candidate_precision = candidate.get("precision")

        checks = {
            "roc_auc_threshold": self._meets(candidate_auc, self.config.min_roc_auc),
            "recall_threshold": self._meets(candidate_recall, self.config.min_recall),
            "precision_threshold": self._meets(candidate_precision, self.config.min_precision),
            "roc_auc_improvement": (
                champion_auc is not None
                and candidate_auc is not None
                and candidate_auc >= champion_auc + self.config.min_roc_auc_improvement
            ),
        }

        if champion_auc is None:
            checks["roc_auc_improvement"] = False

        approved = all(checks.values())
        failed_checks = [name for name, passed in checks.items() if not passed]

        return {
            "decision": "PROMOTE" if approved else "REJECT",
            "approved": approved,
            "checks": checks,
            "failed_checks": failed_checks,
            "champion_roc_auc": champion_auc,
            "candidate_roc_auc": candidate_auc,
            "reason": "All quality gates passed" if approved else "Quality gates failed",
        }

    @staticmethod
    def _meets(value: Any, threshold: float) -> bool:
        return value is not None and float(value) >= threshold
