"""Base tool contract and controlled registry used by AI Engineering agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AgentTool(ABC):
    """A controlled capability that an agent may invoke."""

    name: str
    description: str
    requires_approval: bool = False

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the tool with validated arguments."""
        raise NotImplementedError


class AgentToolRegistry:
    """Allowlist of tools exposed to an agent."""

    def __init__(self, tools: list[AgentTool] | None = None) -> None:
        self._tools: dict[str, AgentTool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: AgentTool) -> None:
        if not tool.name.strip():
            raise ValueError("Tool name must not be empty")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> AgentTool:
        if name not in self._tools:
            raise KeyError(f"Tool is not allowlisted: {name}")
        return self._tools[name]

    def execute(self, name: str, **kwargs: Any) -> Any:
        return self.get(name).run(**kwargs)
