"""Monitoring agent for the first drift investigation workflow."""

from __future__ import annotations

from ai_engineering.schemas.decisions import AgentDecision
from ai_engineering.schemas.events import EngineeringEvent
from ai_engineering.tools.monitoring_tools import MonitoringTools


class MonitoringAgent:
    """Analyzes the existing retraining signal without mutating infrastructure."""

    def __init__(self, tools: MonitoringTools | None = None) -> None:
        self.tools = tools or MonitoringTools()

    def investigate(self, event: EngineeringEvent) -> AgentDecision:
        signal = self.tools.get_retrain_signal()

        if not signal["available"]:
            return AgentDecision(
                action="manual_review",
                reason="Monitoring signal is unavailable, so automated analysis is unsafe.",
                parameters={"event_id": event.event_id},
                requires_human_approval=True,
            )

        if signal["retrain_required"]:
            return AgentDecision(
                action="propose_retraining",
                reason=signal["reason"],
                parameters={
                    "event_id": event.event_id,
                    "drifted_features": signal["drifted_features"],
                },
                requires_human_approval=True,
            )

        return AgentDecision(
            action="no_action",
            reason=signal["reason"],
            parameters={
                "event_id": event.event_id,
                "drifted_features": signal["drifted_features"],
            },
            requires_human_approval=False,
        )
