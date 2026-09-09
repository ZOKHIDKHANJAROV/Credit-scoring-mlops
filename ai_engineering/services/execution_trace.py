"""Execution trace lifecycle built on the audit event layer."""

from __future__ import annotations

from typing import Any

from ai_engineering.schemas.audit import AuditEventType
from ai_engineering.services.audit_service import AuditService


class ExecutionTrace:
    """Record a complete bounded execution lifecycle for one agent request."""

    def __init__(self, audit: AuditService | None = None, trace_id: str | None = None) -> None:
        self.audit = audit or AuditService()
        self.trace_id = trace_id or self.audit.new_trace_id()
        self._closed = False

    def request(self, task: str) -> None:
        self._ensure_open()
        self.audit.record(
            AuditEventType.AGENT_REQUESTED,
            self.trace_id,
            payload={"task": task},
            status="started",
        )

    def tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        self._ensure_open()
        self.audit.record(
            AuditEventType.TOOL_CALLED,
            self.trace_id,
            tool_name=tool_name,
            payload={"arguments": arguments},
            status="started",
        )

    def tool_result(self, tool_name: str, result: Any, status: str = "completed") -> None:
        self._ensure_open()
        self.audit.record(
            AuditEventType.TOOL_RESULT,
            self.trace_id,
            tool_name=tool_name,
            status=status,
            payload={"result": result},
        )

    def approval_requested(self, action: str, reason: str, plan: dict[str, Any]) -> None:
        self._ensure_open()
        self.audit.record(
            AuditEventType.APPROVAL_REQUESTED,
            self.trace_id,
            action=action,
            status="pending",
            payload={"reason": reason, "execution_plan": plan},
        )

    def execution_started(self, action: str) -> None:
        self._ensure_open()
        self.audit.record(
            AuditEventType.EXECUTION_STARTED,
            self.trace_id,
            action=action,
            status="started",
        )

    def execution_completed(self, action: str, result: dict[str, Any]) -> None:
        self._ensure_open()
        self.audit.record(
            AuditEventType.EXECUTION_COMPLETED,
            self.trace_id,
            action=action,
            status="completed",
            payload={"result": result},
        )
        self._closed = True

    def execution_failed(self, action: str, error: str, result: dict[str, Any] | None = None) -> None:
        self._ensure_open()
        self.audit.record(
            AuditEventType.EXECUTION_FAILED,
            self.trace_id,
            action=action,
            status="failed",
            payload={"result": result or {}},
            error=error,
        )
        self._closed = True

    def events(self):
        return self.audit.trace(self.trace_id)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Execution trace is already closed")
