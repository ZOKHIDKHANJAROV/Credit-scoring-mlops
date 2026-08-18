"""Thread-safe append-only audit event storage."""

from __future__ import annotations

from threading import RLock
from ai_engineering.schemas.audit import AuditEvent, AuditEventType


class AuditStore:
    """In-memory audit store with explicit query filters.

    The interface is persistence-agnostic so a PostgreSQL implementation can
    replace this class without changing the service or agent contracts.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def append(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            self._events.append(event)
        return event

    def list(
        self,
        *,
        trace_id: str | None = None,
        event_type: AuditEventType | None = None,
        limit: int | None = None,
    ) -> list[AuditEvent]:
        if limit is not None and (limit < 1 or limit > 1000):
            raise ValueError("limit must be between 1 and 1000")

        with self._lock:
            events = list(self._events)

        if trace_id is not None:
            events = [event for event in events if event.trace_id == trace_id]
        if event_type is not None:
            events = [event for event in events if event.event_type == event_type]

        events.reverse()
        return events[:limit] if limit is not None else events

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
