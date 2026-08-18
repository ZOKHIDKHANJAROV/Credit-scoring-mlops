"""In-memory audit store for the first Command Center implementation."""

from __future__ import annotations

from collections.abc import Iterable

from ai_engineering.schemas.audit import AuditEvent, AuditEventType


class AuditStore:
    """Append-only audit storage with small query capabilities.

    The store is deliberately dependency-free for the local/Kubernetes MVP.
    It can later be replaced by PostgreSQL or another durable event store
    without changing the event contract or API layer.
    """

    def __init__(self, max_events: int = 5000) -> None:
        if max_events < 1:
            raise ValueError("max_events must be greater than zero")
        self.max_events = max_events
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        self._events.append(event)
        if len(self._events) > self.max_events:
            del self._events[: len(self._events) - self.max_events]
        return event

    def record(
        self,
        event_type: AuditEventType,
        *,
        actor: str = "system",
        correlation_id: str | None = None,
        approval_id: str | None = None,
        tool_name: str | None = None,
        status: str | None = None,
        message: str | None = None,
        data: dict | None = None,
    ) -> AuditEvent:
        return self.append(
            AuditEvent(
                event_type=event_type,
                actor=actor,
                correlation_id=correlation_id,
                approval_id=approval_id,
                tool_name=tool_name,
                status=status,
                message=message,
                data=data or {},
            )
        )

    def list(
        self,
        *,
        event_type: AuditEventType | None = None,
        approval_id: str | None = None,
        correlation_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        events: Iterable[AuditEvent] = reversed(self._events)
        if event_type is not None:
            events = (event for event in events if event.event_type == event_type)
        if approval_id is not None:
            events = (event for event in events if event.approval_id == approval_id)
        if correlation_id is not None:
            events = (event for event in events if event.correlation_id == correlation_id)

        return list(events)[:limit]

    def count(self) -> int:
        return len(self._events)
