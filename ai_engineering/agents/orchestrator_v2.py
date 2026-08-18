"""Deterministic multi-agent orchestrator for the AI Engineering Command Center.

The orchestrator coordinates read-only monitoring and model evaluation and turns
results into a proposed action. Mutating actions are never executed here. They
must pass through the existing human-approval workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_engineering.agents.ml_agent import MLAgent
from ai_engineering.tools.kubernetes_tools import KubernetesTools
from ai_engineering.tools.monitoring_tools import MonitoringTools


@dataclass(frozen=True)
class OrchestrationResult:
    """Final decision produced by the command-center pipeline."""

    status: str
    action: str
    reason: str
    requires_human_approval: bool
    stages: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


class CommandCenterOrchestrator:
    """Coordinate monitoring -> evaluation -> approval planning.

    Every stage is deterministic and read-only. Kubernetes and MLflow mutation
    are deliberately outside this class and can only happen after approval.
    """

    def __init__(
        self,
        monitoring: MonitoringTools | None = None,
        ml_agent: MLAgent | None = None,
        kubernetes: KubernetesTools | None = None,
    ) -> None:
        self.monitoring = monitoring or MonitoringTools()
        self.ml_agent = ml_agent or MLAgent()
        self.kubernetes = kubernetes or KubernetesTools()

    def run(self, task: str = "auto") -> OrchestrationResult:
        """Run the bounded engineering decision pipeline."""
        normalized_task = task.strip().lower()
        if not normalized_task:
            normalized_task = "auto"

        stages: list[str] = []
        signal = self._inspect_monitoring()
        stages.append("monitoring")

        if normalized_task in {"monitor", "monitoring", "status"}:
            return OrchestrationResult(
                status="completed",
                action="no_action" if not signal["retrain_required"] else "investigate",
                reason=signal["reason"],
                requires_human_approval=False,
                stages=stages,
                data={"monitoring": signal},
            )

        if not signal["available"]:
            return OrchestrationResult(
                status="manual_review",
                action="request_human_approval",
                reason="Monitoring signal is unavailable; engineering state cannot be established safely.",
                requires_human_approval=True,
                stages=stages,
                data={"monitoring": signal},
            )

        if not signal["retrain_required"] and normalized_task == "auto":
            return OrchestrationResult(
                status="completed",
                action="no_action",
                reason=signal["reason"],
                requires_human_approval=False,
                stages=stages,
                data={"monitoring": signal},
            )

        evaluation = self._evaluate_models()
        stages.append("evaluation")

        if evaluation["decision"] == "REJECT":
            return OrchestrationResult(
                status="completed",
                action="no_action",
                reason=evaluation["reason"],
                requires_human_approval=False,
                stages=stages,
                data={"monitoring": signal, "evaluation": evaluation},
            )

        if evaluation["decision"] != "PROMOTE":
            return OrchestrationResult(
                status="manual_review",
                action="request_human_approval",
                reason=evaluation["reason"],
                requires_human_approval=True,
                stages=stages,
                data={"monitoring": signal, "evaluation": evaluation},
            )

        stages.append("reviewer")
        job_plan = self._build_training_plan(signal)
        stages.append("approval")

        return OrchestrationResult(
            status="approval_required",
            action="create_training_job",
            reason="Drift requires retraining and the evaluated candidate passed quality gates.",
            requires_human_approval=True,
            stages=stages,
            data={
                "monitoring": signal,
                "evaluation": evaluation,
                "kubernetes_job": job_plan,
            },
        )

    def _inspect_monitoring(self) -> dict[str, Any]:
        return self.monitoring.get_retrain_signal()

    def _evaluate_models(self) -> dict[str, Any]:
        return self.ml_agent.evaluate()

    def _build_training_plan(self, signal: dict[str, Any]) -> dict[str, Any]:
        return self.kubernetes.get_training_job_plan()
