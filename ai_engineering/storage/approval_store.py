"""Small in-memory approval store for the first local workflow."""

from __future__ import annotations

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus


class ApprovalStore:
    """Store approval requests without introducing a database dependency yet."""

    def __init__(self) -> None:
        self._items: dict[str, ApprovalRequest] = {}

    def create(self, request: ApprovalRequest) -> ApprovalRequest:
        if request.approval_id in self._items:
            raise ValueError(f"Approval already exists: {request.approval_id}")
        self._items[request.approval_id] = request
        return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._items.get(approval_id)

    def list_all(self) -> list[ApprovalRequest]:
        return list(self._items.values())

    def list_pending(self) -> list[ApprovalRequest]:
        return [item for item in self._items.values() if item.status == ApprovalStatus.PENDING]

    def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        request = self._items.get(decision.approval_id)
        if request is None:
            raise KeyError(f"Approval not found: {decision.approval_id}")
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is already {request.status.value}")

        request.status = ApprovalStatus.APPROVED if decision.approved else ApprovalStatus.REJECTED
        request.decided_at = decision.decided_at
        request.decided_by = decision.decided_by
        request.decision_comment = decision.comment
        return request

    def mark_executing(self, approval_id: str) -> ApprovalRequest:
        request = self._get(approval_id)
        if request.status != ApprovalStatus.APPROVED:
            raise ValueError(
                f"Only approved requests can execute; current status is {request.status.value}"
            )
        request.status = ApprovalStatus.EXECUTING
        return request

    def update_execution_result(self, approval_id: str, result: dict) -> ApprovalRequest:
        request = self._get(approval_id)
        if request.status != ApprovalStatus.EXECUTING:
            raise ValueError(
                f"Only executing requests can update; current status is {request.status.value}"
            )
        request.execution_result = result
        return request

    def mark_completed(self, approval_id: str, result: dict) -> ApprovalRequest:
        request = self._get(approval_id)
        if request.status != ApprovalStatus.EXECUTING:
            raise ValueError(
                f"Only executing requests can complete; current status is {request.status.value}"
            )
        request.status = ApprovalStatus.COMPLETED
        request.execution_result = result
        return request

    def mark_failed(self, approval_id: str, result: dict) -> ApprovalRequest:
        request = self._get(approval_id)
        if request.status != ApprovalStatus.EXECUTING:
            raise ValueError(
                f"Only executing requests can fail; current status is {request.status.value}"
            )
        request.status = ApprovalStatus.FAILED
        request.execution_result = result
        return request

    def _get(self, approval_id: str) -> ApprovalRequest:
        request = self._items.get(approval_id)
        if request is None:
            raise KeyError(f"Approval not found: {approval_id}")
        return request
