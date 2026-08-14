"""Deterministic first version of the drift-to-retraining workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_engineering.agents.ml_agent import MLAgent
from ai_engineering.agents.monitoring_agent import MonitoringAgent
from ai_engineering.tools.kubernetes_tools import KubernetesTools
from ai_engineering.tools.mlflow_tools import MLflowTools
from ai_engineering.tools.monitoring_tools import MonitoringTools


@dataclass(frozen=True)
class RetrainingPlan:
    """A proposed action. Execution is intentionally separate."""

    status: str
    reason: str
    drifted_features: list[str]
    champion: dict[str, Any]
    model_comparison: list[dict[str, Any]]
    kubernetes_job: dict[str, Any] | None = None


class RetrainingWorkflow:
    """Coordinate monitoring, ML analysis and Kubernetes planning."""

    def __init__(self, signal_path: str = "reports/retrain_signal.json") -> None:
        monitoring_tools = MonitoringTools(signal_path=signal_path)
        mlflow_tools = MLflowTools()
        self.monitoring_agent = MonitoringAgent(monitoring_tools)
        self.ml_agent = MLAgent(mlflow_tools)
        self.kubernetes_tools = KubernetesTools()

    def build_plan(self) -> RetrainingPlan:
        signal = self.monitoring_agent.inspect()

        if not signal["retrain_required"]:
            return RetrainingPlan(
                status="no_action",
                reason=signal["reason"],
                drifted_features=signal["drifted_features"],
                champion=self.ml_agent.get_champion(),
                model_comparison=self.ml_agent.compare_models(),
            )

        comparison = self.ml_agent.compare_models()
        champion = self.ml_agent.get_champion()
        job = self.kubernetes_tools.build_training_job_plan(
            reason=signal["reason"],
            drifted_features=signal["drifted_features"],
        )

        return RetrainingPlan(
            status="approval_required",
            reason=signal["reason"],
            drifted_features=signal["drifted_features"],
            champion=champion,
            model_comparison=comparison,
            kubernetes_job=job,
        )
