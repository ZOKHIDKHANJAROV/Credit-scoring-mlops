"""Recovery and reconciliation for uncertain Kubernetes executions."""

from __future__ import annotations

from typing import Any

from ai_engineering.observability import EXECUTION_RETRIES_TOTAL
from ai_engineering.schemas.approvals import ApprovalRequest, ApprovalStatus
from ai_engineering.schemas.audit import AuditEventType
from ai_engineering.services.audit_service import AuditService
from ai_engineering.storage.approval_store import ApprovalStore


class ReconciliationService:
    """Resolve UNKNOWN executions without allowing blind duplicate execution."""

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

        self.audit_service.record(
            AuditEventType.EXECUTION_RECONCILIATION_STARTED,
            trace_id=approval.trace_id,
            action=approval.action,
            status=approval.status.value,
        )
        job_name = f"credit-training-{approval_id}"
        result = self.executor.get_training_job_status(job_name)

        if result.get("exists") and result.get("status") == "completed":
            recovered = self.store.mark_completed(
                approval_id, {"executed": True, "reconciled": True, **result}
            )
        elif result.get("exists") and result.get("status") == "failed":
            recovered = self.store.mark_failed(
                approval_id, {"executed": False, "reconciled": True, **result}
            )
        else:
            recovered = approval

        self.audit_service.record(
            AuditEventType.EXECUTION_RECONCILIATION_COMPLETED,
            trace_id=approval.trace_id,
            action=approval.action,
            status=recovered.status.value,
            payload=result,
        )
        return recovered

    def retry_if_absent(self, approval_id: str) -> ApprovalRequest:
        """Claim retry ownership before reading Kubernetes or creating a Job."""
        approval = self.store.get(approval_id)
        if approval is None:
            raise KeyError(f"Approval not found: {approval_id}")
        if approval.status != ApprovalStatus.UNKNOWN:
            return approval

        self.audit_service.record(
            AuditEventType.EXECUTION_RECONCILIATION_STARTED,
            trace_id=approval.trace_id,
            action=approval.action,
            status=approval.status.value,
        )

        claimed, owns_retry = self.store.claim_retry_execution(approval_id)
        if not owns_retry:
            return claimed

        job_name = f"credit-training-{approval_id}"
        try:
            result = self.executor.get_training_job_status(job_name)
        except Exception as exc:
            return self.store.mark_unknown(
                approval_id,
                {"executed": False, "unknown": True, "error": str(exc)},
            )

        if result.get("exists") and result.get("status") == "completed":
            recovered = self.store.mark_completed(
                approval_id, {"executed": True, "reconciled": True, **result}
            )
            self.audit_service.record(
                AuditEventType.EXECUTION_RECONCILIATION_COMPLETED,
                trace_id=approval.trace_id,
                action=approval.action,
                status=recovered.status.value,
                payload=result,
            )
            return recovered

        if result.get("exists") and result.get("status") == "failed":
            recovered = self.store.mark_failed(
                approval_id, {"executed": False, "reconciled": True, **result}
            )
            self.audit_service.record(
                AuditEventType.EXECUTION_RECONCILIATION_COMPLETED,
                trace_id=approval.trace_id,
                action=approval.action,
                status=recovered.status.value,
                payload=result,
            )
            return recovered

        if result.get("exists"):
            self.audit_service.record(
                AuditEventType.EXECUTION_RECONCILIATION_COMPLETED,
                trace_id=approval.trace_id,
                action=approval.action,
                status=ApprovalStatus.EXECUTING.value,
                payload=result,
            )
            return self.store.get(approval_id) or claimed

        if result.get("status") != "absent":
            return self.store.mark_unknown(
                approval_id,
                {"executed": False, "unknown": True, "reconciliation": result},
            )

        self.audit_service.record(
            AuditEventType.EXECUTION_RETRY,
            trace_id=approval.trace_id,
            action=approval.action,
            status="retrying",
            payload=result,
        )
        EXECUTION_RETRIES_TOTAL.labels(action=approval.action).inc()

        try:
            execution = self.executor.apply_training_job(approved=True, execution_id=approval_id)
        except Exception as exc:
            return self.store.mark_unknown(
                approval_id, {"executed": False, "unknown": True, "error": str(exc)}
            )
        if execution.get("executed") is True:
            return self.store.mark_completed(approval_id, {**execution, "reconciled_retry": True})
        return self.store.mark_failed(approval_id, execution)
