"""In-memory approval store with explicit state-transition guards."""

from __future__ import annotations

from threading import RLock

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus


class InvalidApprovalTransition(ValueError):
    """Raised when an approval attempts an illegal state transition."""


class ApprovalStore:
    """Thread-safe approval state machine for the local workflow."""

    _TRANSITIONS: dict[ApprovalStatus, frozenset[ApprovalStatus]] = {
        ApprovalStatus.PENDING: frozenset({ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}),
        ApprovalStatus.APPROVED: frozenset({ApprovalStatus.EXECUTING}),
        ApprovalStatus.REJECTED: frozenset(),
        ApprovalStatus.EXECUTING: frozenset({ApprovalStatus.COMPLETED, ApprovalStatus.FAILED}),
        ApprovalStatus.COMPLETED: frozenset(),
        ApprovalStatus.FAILED: frozenset(),
    }

    def __init__(self) -> None:
        self._items: dict[str, ApprovalRequest] = {}
        self._lock = RLock()

    def create(self, request: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            if request.approval_id in self._items:
                raise ValueError(f"Approval already exists: {request.approval_id}")
            if request.status != ApprovalStatus.PENDING:
                raise InvalidApprovalTransition("New approvals must start in pending state")
            self._items[request.approval_id] = request
            return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        with self._lock:
            return self._items.get(approval_id)

    def list_pending(self) -> list[ApprovalRequest]:
        with self._lock:
            return [item for item in self._items.values() if item.status == ApprovalStatus.PENDING]

    def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        with self._lock:
            request = self._get(decision.approval_id)
            target = ApprovalStatus.APPROVED if decision.approved else ApprovalStatus.REJECTED
            self._transition(request, target)
            request.decided_at = decision.decided_at
            request.decided_by = decision.decided_by
            request.decision_comment = decision.comment
            return request

    def mark_executing(self, approval_id: str) -> ApprovalRequest:
        with self._lock:
            request = self._get(approval_id)
            self._transition(request, ApprovalStatus.EXECUTING)
            return request

    def mark_completed(self, approval_id: str, result: dict) -> ApprovalRequest:
        with self._lock:
            request = self._get(approval_id)
            self._transition(request, ApprovalStatus.COMPLETED)
            request.execution_result = result
            return request

    def mark_failed(self, approval_id: str, result: dict) -> ApprovalRequest:
        with self._lock:
            request = self._get(approval_id)
            self._transition(request, ApprovalStatus.FAILED)
            request.execution_result = result
            return request

    def _transition(self, request: ApprovalRequest, target: ApprovalStatus) -> None:
        allowed = self._TRANSITIONS[request.status]
        if target not in allowed:
            raise InvalidApprovalTransition(
                f"Invalid approval transition: {request.status.value} -> {target.value}"
            )
        request.status = target

    def _get(self, approval_id: str) -> ApprovalRequest:
        request = self._items.get(approval_id)
        if request is None:
            raise KeyError(f"Approval not found: {approval_id}")
        return request
