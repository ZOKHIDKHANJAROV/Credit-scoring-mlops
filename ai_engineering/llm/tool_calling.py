"""Bounded tool-calling loop for OpenAI-compatible LLMs such as vLLM."""

from __future__ import annotations

import json
from typing import Any

from ai_engineering.llm.provider import OpenAICompatibleProvider
from ai_engineering.schemas.audit import AuditEventType
from ai_engineering.services.audit_service import AuditService
from ai_engineering.tools.registry import ToolRegistry


class ToolCallingAgent:
    """Run a bounded reasoning loop where the LLM can call allowlisted tools."""

    def __init__(
        self,
        provider: OpenAICompatibleProvider,
        registry: ToolRegistry,
        max_rounds: int = 4,
        audit_service: AuditService | None = None,
    ) -> None:
        if max_rounds < 1 or max_rounds > 10:
            raise ValueError("max_rounds must be between 1 and 10")
        self.provider = provider
        self.registry = registry
        self.max_rounds = max_rounds
        self.audit = audit_service or AuditService()

    def run(self, task: str) -> dict[str, Any]:
        """Run the agent and return the final answer, tools, and trace ID."""
        trace_id = self.audit.new_trace_id()
        self.audit.record(
            AuditEventType.AGENT_REQUESTED,
            trace_id,
            payload={"task": task},
            status="started",
        )

        try:
            from openai import OpenAI
        except ImportError as exc:
            self.audit.record(
                AuditEventType.EXECUTION_FAILED,
                trace_id,
                status="failed",
                error="Install the 'openai' package to use tool calling",
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
                answer = message.content or ""
                self.audit.record(
                    AuditEventType.EXECUTION_COMPLETED,
                    trace_id,
                    status="completed",
                    payload={"rounds": round_number, "tools_used": used_tools, "answer": answer},
                )
                return {
                    "status": "completed",
                    "answer": answer,
                    "tools_used": used_tools,
                    "trace_id": trace_id,
                }

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
                self.audit.record(
                    AuditEventType.TOOL_CALLED,
                    trace_id,
                    tool_name=name,
                    status="requested",
                    payload={"arguments": call.function.arguments},
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

                tool_status = "failed" if "error" in result else "completed"
                self.audit.record(
                    AuditEventType.TOOL_RESULT,
                    trace_id,
                    tool_name=name,
                    status=tool_status,
                    payload={"result": result},
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

        self.audit.record(
            AuditEventType.EXECUTION_FAILED,
            trace_id,
            status="max_rounds_exceeded",
            error="The agent reached the maximum number of tool-calling rounds.",
            payload={"rounds": self.max_rounds, "tools_used": used_tools},
        )
        return {
            "status": "max_rounds_exceeded",
            "answer": "The agent reached the maximum number of tool-calling rounds.",
            "tools_used": used_tools,
            "trace_id": trace_id,
        }
