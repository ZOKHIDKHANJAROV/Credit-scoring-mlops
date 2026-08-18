"""Audit event contracts for the AI Engineering Command Center."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    AGENT_RUN_STARTED = "agent_run_started"
    AGENT_RUN_COMPLETED = "agent_run_completed"
    TOOL_CALL = "tool_call"
    APPROVAL_CREATED = "approval_created"
    APPROVAL_DECIDED = "approval_decided"
    APPROVAL_EXECUTION_STARTED = "approval_execution_started"
    APPROVAL_EXECUTION_COMPLETED = "approval_execution_completed"
    APPROVAL_EXECUTION_FAILED = "approval_execution_failed"


class AuditEvent(BaseModel):
    """Immutable record of an important agent-control-plane transition."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    actor: str = "system"
    correlation_id: str | None = None
    approval_id: str | None = None
    tool_name: str | None = None
    status: str | None = None
    message: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
