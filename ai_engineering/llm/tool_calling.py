"""Bounded tool-calling loop for OpenAI-compatible LLMs such as vLLM."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from ai_engineering.llm.provider import OpenAICompatibleProvider
from ai_engineering.schemas.audit import AuditEventType
from ai_engineering.storage.audit_store import AuditStore
from ai_engineering.tools.registry import ToolRegistry


class ToolCallingAgent:
    """Run a bounded reasoning loop where the LLM can call allowlisted tools."""

    def __init__(
        self,
        provider: OpenAICompatibleProvider,
        registry: ToolRegistry,
        max_rounds: int = 4,
        audit_store: AuditStore | None = None,
    ) -> None:
        if max_rounds < 1 or max_rounds > 10:
            raise ValueError("max_rounds must be between 1 and 10")
        self.provider = provider
        self.registry = registry
        self.max_rounds = max_rounds
        self.audit_store = audit_store

    def run(self, task: str) -> dict[str, Any]:
        """Run the agent and return its final text plus executed read-only tools."""
        correlation_id = str(uuid4())
        self._audit(
            AuditEventType.AGENT_RUN_STARTED,
            correlation_id=correlation_id,
            message="Agent run started",
            data={"task": task},
        )

        try:
            from openai import OpenAI
        except ImportError as exc:
            self._audit(
                AuditEventType.AGENT_RUN_COMPLETED,
                correlation_id=correlation_id,
                status="failed",
                message="OpenAI client dependency is missing",
            )
            raise RuntimeError("Install the 'openai' package to use tool calling") from exc

        client = OpenAI(base_url=self.provider.base_url, api_key=self.provider.api_key)
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are the AI Engineering Command Center orchestrator. "
                    "Analyze the engineering task using only registered tools. "
                    "Never invent tool results. Never execute destructive actions. "
                    "For actions that change infrastructure or models, request human approval."
                ),
            },
            {"role": "user", "content": task},
        ]
        used_tools: list[str] = []

        for round_number in range(1, self.max_rounds + 1):
            response = client.chat.completions.create(
                model=self.provider.model,
                messages=messages,
                tools=self.registry.definitions(),
                tool_choice="auto",
                temperature=0.0,
            )
            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                result = {
                    "status": "completed",
                    "answer": message.content or "",
                    "tools_used": used_tools,
                }
                self._audit(
                    AuditEventType.AGENT_RUN_COMPLETED,
                    correlation_id=correlation_id,
                    status="completed",
                    message="Agent run completed",
                    data={"rounds": round_number, "tools_used": used_tools},
                )
                return result

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [],
            }

            for call in tool_calls:
                assistant_message["tool_calls"].append(
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                )
            messages.append(assistant_message)

            for call in tool_calls:
                name = call.function.name
                self._audit(
                    AuditEventType.TOOL_CALL,
                    correlation_id=correlation_id,
                    tool_name=name,
                    status="requested",
                    message="LLM requested tool execution",
                    data={"arguments": call.function.arguments},
                )
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    result = {"error": "Invalid JSON tool arguments"}
                else:
                    try:
                        result = self.registry.execute(name, arguments)
                        used_tools.append(name)
                    except (KeyError, TypeError, ValueError) as exc:
                        result = {"error": str(exc)}

                self._audit(
                    AuditEventType.TOOL_CALL,
                    correlation_id=correlation_id,
                    tool_name=name,
                    status="completed" if "error" not in result else "failed",
                    message="Tool execution completed",
                    data={"result": result},
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

        result = {
            "status": "max_rounds_exceeded",
            "answer": "The agent reached the maximum number of tool-calling rounds.",
            "tools_used": used_tools,
        }
        self._audit(
            AuditEventType.AGENT_RUN_COMPLETED,
            correlation_id=correlation_id,
            status="max_rounds_exceeded",
            message="Agent reached maximum tool-calling rounds",
            data={"rounds": self.max_rounds, "tools_used": used_tools},
        )
        return result

    def _audit(
        self,
        event_type: AuditEventType,
        *,
        correlation_id: str,
        status: str | None = None,
        message: str | None = None,
        tool_name: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        if self.audit_store is None:
            return
        self.audit_store.record(
            event_type,
            actor="agent",
            correlation_id=correlation_id,
            tool_name=tool_name,
            status=status,
            message=message,
            data=data,
        )
