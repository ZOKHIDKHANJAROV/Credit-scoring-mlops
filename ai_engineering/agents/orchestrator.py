"""Initial orchestration skeleton for the AI Engineering Command Center."""

from typing import Iterable

from ai_engineering.schemas.decisions import AgentDecision
from ai_engineering.schemas.events import EngineeringEvent
from ai_engineering.tools.base import AgentTool


class OrchestratorAgent:
    """Routes engineering events to controlled tools.

    The first implementation is intentionally deterministic. An LLM planner will
    be introduced only after the tool contracts and safety policies are tested.
    """

    def __init__(self, tools: Iterable[AgentTool] = ()) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def handle(self, event: EngineeringEvent) -> AgentDecision:
        """Create a safe proposal for the incoming event."""
        if event.event_type == "model_drift_detected":
            return AgentDecision(
                action="investigate_model_drift",
                reason=(
                    "Model drift was detected. Investigate production data and "
                    "model metrics before considering retraining."
                ),
                parameters={"event_id": event.event_id},
                requires_human_approval=False,
            )

        return AgentDecision(
            action="manual_review",
            reason=f"No workflow registered for event type: {event.event_type}",
            parameters={"event_id": event.event_id},
            requires_human_approval=True,
        )
