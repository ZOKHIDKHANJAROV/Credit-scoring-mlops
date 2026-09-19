from types import SimpleNamespace
from unittest.mock import Mock

from ai_engineering.schemas.approvals import ApprovalStatus
from ai_engineering.schemas.audit import AuditEventType
from ai_engineering.services.reconciliation_service import ReconciliationService


def test_retry_loser_does_not_emit_reconciliation_started():
    request = SimpleNamespace(
        approval_id="approval-1",
        trace_id="trace-1",
        action="create_training_job",
        status=ApprovalStatus.UNKNOWN,
    )
    claimed = SimpleNamespace(
        approval_id="approval-1",
        trace_id="trace-1",
        action="create_training_job",
        status=ApprovalStatus.EXECUTING,
    )

    store = Mock()
    store.get.return_value = request
    store.claim_retry_execution.return_value = (claimed, False)
    audit = Mock()
    executor = Mock()

    service = ReconciliationService(store, executor, audit)
    result = service.retry_if_absent("approval-1")

    assert result is claimed
    audit.record.assert_not_called()
    executor.get_training_job_status.assert_not_called()
    executor.apply_training_job.assert_not_called()


def test_retry_owner_emits_started_after_atomic_claim():
    request = SimpleNamespace(
        approval_id="approval-1",
        trace_id="trace-1",
        action="create_training_job",
        status=ApprovalStatus.UNKNOWN,
    )
    claimed = SimpleNamespace(
        approval_id="approval-1",
        trace_id="trace-1",
        action="create_training_job",
        status=ApprovalStatus.EXECUTING,
    )

    store = Mock()
    store.get.return_value = request
    store.claim_retry_execution.return_value = (claimed, True)
    store.mark_completed.return_value = SimpleNamespace(status=ApprovalStatus.COMPLETED)
    executor = Mock()
    executor.get_training_job_status.return_value = {
        "exists": True,
        "status": "completed",
    }
    audit = Mock()

    service = ReconciliationService(store, executor, audit)
    result = service.retry_if_absent("approval-1")

    assert result.status == ApprovalStatus.COMPLETED
    events = [call.args[0] for call in audit.record.call_args_list]
    assert events[0] == AuditEventType.EXECUTION_RECONCILIATION_STARTED
