"""Base tool contract used by all AI Engineering agents."""

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
