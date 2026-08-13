"""Orchestrator for the AI Engineering Command Center."""

from __future__ import annotations

from typing import Iterable

from ai_engineering.agents.monitoring_agent import MonitoringAgent
from ai_engineering.schemas.decisions import AgentDecision
from ai_engineering.schemas.events import EngineeringEvent
from ai_engineering.tools.base import AgentTool


class OrchestratorAgent:
    """Routes engineering events to controlled agent workflows."""

    def __init__(
        self,
        tools: Iterable[AgentTool] = (),
        monitoring_agent: MonitoringAgent | None = None,
    ) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self.monitoring_agent = monitoring_agent or MonitoringAgent()

    def handle(self, event: EngineeringEvent) -> AgentDecision:
        """Run the registered workflow for an engineering event."""
        if event.event_type == "model_drift_detected":
            return self.monitoring_agent.investigate(event)

        return AgentDecision(
            action="manual_review",
            reason=f"No workflow registered for event type: {event.event_type}",
            parameters={"event_id": event.event_id},
            requires_human_approval=True,
        )
