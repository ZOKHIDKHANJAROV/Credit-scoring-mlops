"""Application service for recording command-center audit events."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from ai_engineering.schemas.audit import AuditEvent, AuditEventType
from ai_engineering.storage.audit_store import AuditStore


class AuditService:
    """Create structured audit events without coupling callers to storage."""

    def __init__(self, store: AuditStore | None = None) -> None:
        self.store = store or AuditStore()

    def new_trace_id(self) -> str:
        return str(uuid4())

    def record(
        self,
        event_type: AuditEventType,
        trace_id: str,
        *,
        actor: str = "ai-engineering-agent",
        action: str | None = None,
        tool_name: str | None = None,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> AuditEvent:
        return self.store.append(
            AuditEvent(
                event_type=event_type,
                trace_id=trace_id,
                actor=actor,
                action=action,
                tool_name=tool_name,
                status=status,
                payload=payload or {},
                error=error,
            )
        )

    def trace(self, trace_id: str) -> list[AuditEvent]:
        return self.store.list(trace_id=trace_id)
