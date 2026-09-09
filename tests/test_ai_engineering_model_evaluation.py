from __future__ import annotations

from typing import Any

from ai_engineering.agents.ml_agent import MLAgent
from ai_engineering.agents.reviewer_agent import QualityGateConfig, ReviewerAgent


class FakeMLflowTools:
    def __init__(self, champion: dict[str, Any], candidate: dict[str, Any]) -> None:
        self.champion = champion
        self.candidate = candidate

    def get_champion_model(self) -> dict[str, Any]:
        return self.champion

    def compare_latest_models(self) -> list[dict[str, Any]]:
        return [self.candidate]

    def get_run_metrics(self, run_id: str) -> dict[str, Any]:
        if run_id == self.champion.get("run_id"):
            return {"available": True, "run_id": run_id, "metrics": self.champion["metrics"]}
        if run_id == self.candidate.get("run_id"):
            return {"available": True, "run_id": run_id, "metrics": self.candidate["metrics"]}
        return {"available": False, "run_id": run_id}


def test_reviewer_promotes_candidate_when_all_quality_gates_pass() -> None:
    reviewer = ReviewerAgent(
        QualityGateConfig(
            min_roc_auc=0.80,
            min_recall=0.60,
            min_precision=0.50,
            min_roc_auc_improvement=0.01,
        )
    )

    result = reviewer.review(
        champion={"roc_auc": 0.82},
        candidate={"roc_auc": 0.84, "recall": 0.70, "precision": 0.60},
    )

    assert result["decision"] == "PROMOTE"
    assert result["approved"] is True
    assert result["failed_checks"] == []


def test_reviewer_rejects_candidate_when_quality_gate_fails() -> None:
    reviewer = ReviewerAgent()

    result = reviewer.review(
        champion={"roc_auc": 0.82},
        candidate={"roc_auc": 0.81, "recall": 0.55, "precision": 0.60},
    )

    assert result["decision"] == "REJECT"
    assert result["approved"] is False
    assert "recall_threshold" in result["failed_checks"]
    assert "roc_auc_improvement" in result["failed_checks"]


def test_ml_agent_returns_manual_review_without_candidates() -> None:
    class EmptyTools(FakeMLflowTools):
        def __init__(self) -> None:
            pass

        def get_champion_model(self) -> dict[str, Any]:
            return {"available": True, "run_id": "champion"}

        def compare_latest_models(self) -> list[dict[str, Any]]:
            return []

    result = MLAgent(tools=EmptyTools()).evaluate()

    assert result["decision"] == "MANUAL_REVIEW"
    assert result["requires_human_approval"] is True


def test_ml_agent_returns_manual_review_when_champion_metrics_are_unavailable() -> None:
    tools = FakeMLflowTools(
        champion={"available": False, "run_id": "champion"},
        candidate={
            "run_name": "catboost_baseline",
            "run_id": "candidate",
            "metrics": {"roc_auc": 0.84, "recall": 0.70, "precision": 0.60},
        },
    )

    result = MLAgent(tools=tools).evaluate()

    assert result["decision"] == "MANUAL_REVIEW"
    assert result["requires_human_approval"] is True


def test_ml_agent_evaluates_candidate_without_mutating_tools() -> None:
    tools = FakeMLflowTools(
        champion={
            "available": True,
            "run_id": "champion",
            "version": "3",
            "metrics": {"roc_auc": 0.82, "recall": 0.65, "precision": 0.55},
        },
        candidate={
            "run_name": "catboost_baseline",
            "run_id": "candidate",
            "metrics": {"roc_auc": 0.84, "recall": 0.70, "precision": 0.60},
        },
    )

    result = MLAgent(tools=tools).evaluate()

    assert result["decision"] == "PROMOTE"
    assert result["requires_human_approval"] is True
    assert result["quality_review"]["approved"] is True
    assert tools.champion["version"] == "3"
