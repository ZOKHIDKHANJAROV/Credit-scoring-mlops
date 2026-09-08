"""Recovery and reconciliation for uncertain Kubernetes executions."""

from __future__ import annotations

from typing import Any

from ai_engineering.schemas.approvals import ApprovalRequest, ApprovalStatus
from ai_engineering.services.audit_service import AuditService
from ai_engineering.schemas.audit import AuditEventType
from ai_engineering.storage.approval_store import ApprovalStore


class ReconciliationService:
    def __init__(self, store: ApprovalStore, executor: Any, audit_service: AuditService) -> None:
        self.store = store
        self.executor = executor
        self.audit_service = audit_service

    def reconcile(self, approval_id: str) -> ApprovalRequest:
        approval = self.store.get(approval_id)
        if approval is None:
            raise KeyError(f"Approval not found: {approval_id}")
        if approval.status != ApprovalStatus.UNKNOWN:
            return approval

        self.audit_service.record(AuditEventType.EXECUTION_RECONCILIATION_STARTED, trace_id=approval_id, action=approval.action, status=approval.status.value)
        job_name = f"credit-training-{approval_id}"
        result = self.executor.get_training_job_status(job_name)

        if result.get("exists") and result.get("status") == "completed":
            recovered = self.store.mark_completed(approval_id, {"executed": True, "reconciled": True, **result})
        elif result.get("exists") and result.get("status") == "failed":
            recovered = self.store.mark_failed(approval_id, {"executed": False, "reconciled": True, **result})
        else:
            recovered = approval

        self.audit_service.record(AuditEventType.EXECUTION_RECONCILIATION_COMPLETED, trace_id=approval_id, action=approval.action, status=recovered.status.value, payload=result)
        return recovered
