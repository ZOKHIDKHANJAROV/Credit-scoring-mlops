"""Small in-memory approval store for the first local workflow."""

from __future__ import annotations

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus


class ApprovalStore:
    """Store pending approvals without introducing a database dependency yet."""

    def __init__(self) -> None:
        self._items: dict[str, ApprovalRequest] = {}

    def create(self, request: ApprovalRequest) -> ApprovalRequest:
        self._items[request.approval_id] = request
        return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._items.get(approval_id)

    def list_pending(self) -> list[ApprovalRequest]:
        return [item for item in self._items.values() if item.status == ApprovalStatus.PENDING]

    def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        request = self._items.get(decision.approval_id)
        if request is None:
            raise KeyError(f"Approval not found: {decision.approval_id}")
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is already {request.status.value}")

        request.status = ApprovalStatus.APPROVED if decision.approved else ApprovalStatus.REJECTED
        return request
