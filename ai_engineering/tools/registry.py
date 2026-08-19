"""Allowlisted tool registry for LLM-driven agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RegisteredTool:
    """A tool exposed to the LLM with an explicit execution contract."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]
    requires_human_approval: bool = False


class ToolRegistry:
    """Registry that exposes only explicitly registered tools."""

    def __init__(self, tools: list[RegisteredTool] | None = None) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: RegisteredTool) -> None:
        """Register one tool and reject duplicate names."""
        if not tool.name.strip():
            raise ValueError("Tool name must not be empty")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool:
        """Return a registered tool or raise a clear allowlist error."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._tools)

    def definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible function definitions for registered tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool only when its contract permits autonomous execution."""
        tool = self.get(name)
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a JSON object")

        if tool.requires_human_approval:
            return {
                "executed": False,
                "requires_human_approval": True,
                "tool": name,
                "reason": "This tool cannot be executed by the LLM without approval.",
            }

        return tool.handler(**arguments)
