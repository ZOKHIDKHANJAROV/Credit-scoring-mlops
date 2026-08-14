"""Orchestrator for the AI Engineering Command Center."""

from __future__ import annotations

import json
from typing import Iterable

from ai_engineering.agents.monitoring_agent import MonitoringAgent
from ai_engineering.llm.provider import LLMProvider, OpenAICompatibleProvider
from ai_engineering.schemas.decisions import AgentDecision
from ai_engineering.schemas.events import EngineeringEvent
from ai_engineering.tools.base import AgentTool, AgentToolRegistry


class OrchestratorAgent:
    """Routes events and tasks through controlled agent workflows."""

    def __init__(
        self,
        tools: Iterable[AgentTool] = (),
        monitoring_agent: MonitoringAgent | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        tool_list = list(tools)
        self._tool_registry = AgentToolRegistry(tool_list)
        self.monitoring_agent = monitoring_agent or MonitoringAgent()
        self.llm_provider = llm_provider or OpenAICompatibleProvider()

    @property
    def available_tools(self) -> list[str]:
        return self._tool_registry.names()

    def handle(self, event: EngineeringEvent) -> AgentDecision:
        """Run the registered deterministic workflow for an engineering event."""
        if event.event_type == "model_drift_detected":
            return self.monitoring_agent.investigate(event)

        return AgentDecision(
            action="manual_review",
            reason=f"No workflow registered for event type: {event.event_type}",
            parameters={"event_id": event.event_id},
            requires_human_approval=True,
        )

    def reason(self, task: str, context: dict | None = None) -> AgentDecision:
        """Ask the LLM for a structured recommendation without executing actions."""
        system_prompt = (
            "You are the reasoning layer of an ML engineering command center. "
            "Never execute infrastructure actions. Return JSON only with keys: "
            "action, reason, confidence, requires_human_approval, tools_used. "
            "Allowed actions: no_action, investigate, propose_retraining, "
            "request_human_approval. Confidence must be a number from 0 to 1. "
            "Dangerous or mutating actions always require human approval."
        )
        user_prompt = json.dumps(
            {
                "task": task,
                "context": context or {},
                "available_tools": self.available_tools,
            },
            ensure_ascii=False,
        )
        raw = self.llm_provider.generate(system_prompt, user_prompt, temperature=0.0)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            return AgentDecision(
                action="manual_review",
                reason=f"LLM returned invalid JSON: {exc}",
                parameters={"raw_response": raw},
                requires_human_approval=True,
            )

        allowed_actions = {
            "no_action",
            "investigate",
            "propose_retraining",
            "request_human_approval",
        }
        action = payload.get("action")
        if action not in allowed_actions:
            return AgentDecision(
                action="manual_review",
                reason="LLM returned an action outside the allowlist.",
                parameters={"llm_response": payload},
                requires_human_approval=True,
            )

        confidence = payload.get("confidence", 0.0)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0

        return AgentDecision(
            action=action,
            reason=str(payload.get("reason", "No reason provided")),
            parameters={"confidence": confidence, "tools_used": payload.get("tools_used", [])},
            requires_human_approval=bool(payload.get("requires_human_approval", True)),
        )
