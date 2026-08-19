"""Audit event schemas for AI Engineering Command Center."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    AGENT_REQUESTED = "agent_requested"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    DECISION_CREATED = "decision_created"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"


class AuditEvent(BaseModel):
    """Immutable event describing one observable agent operation."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: str
    actor: str = "ai-engineering-agent"
    action: str | None = None
    tool_name: str | None = None
    status: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
