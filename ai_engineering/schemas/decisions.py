"""Decision contracts and safety boundaries for agents."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_HUMAN_APPROVAL = "needs_human_approval"


@dataclass(frozen=True)
class AgentDecision:
    """A proposed action produced by an agent."""

    action: str
    status: DecisionStatus = DecisionStatus.PROPOSED
    reason: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_human_approval: bool = True
