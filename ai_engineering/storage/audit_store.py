"""Audit event storage abstraction for the command center."""

from __future__ import annotations

from threading import RLock
from typing import Iterable

from ai_engineering.schemas.audit import AuditEvent


class AuditStore:
    """Thread-safe append-only in-memory audit store.

    The store is intentionally persistence-agnostic so the agent can be tested
    without PostgreSQL. A database-backed implementation can replace it later
    without changing the audit contract.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def append(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            self._events.append(event)
        return event

    def list(self, trace_id: str | None = None) -> list[AuditEvent]:
        with self._lock:
            events: Iterable[AuditEvent] = tuple(self._events)
        if trace_id is not None:
            events = (event for event in events if event.trace_id == trace_id)
        return list(events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
