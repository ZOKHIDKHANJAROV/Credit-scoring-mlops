"""Structured schemas for LLM-driven agent tasks and decisions."""

from __future__ import annotations

from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentAction(str, Enum):
    NO_ACTION = "no_action"
    INVESTIGATE = "investigate"
    PROPOSE_RETRAINING = "propose_retraining"
    REQUEST_HUMAN_APPROVAL = "request_human_approval"


class AgentTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    task: str
    context: dict[str, object] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    task_id: str
    action: AgentAction
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_approval: bool = True
    tools_used: list[str] = Field(default_factory=list)
