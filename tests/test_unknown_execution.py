from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus
from ai_engineering.storage.approval_store import ApprovalStore, InvalidApprovalTransition


def make_request() -> ApprovalRequest:
    return ApprovalRequest(action="create_training_job", reason="drift detected")


def test_unknown_can_be_reconciled_to_completed() -> None:
    store = ApprovalStore()
    request = store.create(make_request())
    store.decide(ApprovalDecision(approval_id=request.approval_id, approved=True))
    store.mark_executing(request.approval_id)
    request = store.mark_unknown(request.approval_id, {"error": "timeout"})
    assert request.status == ApprovalStatus.UNKNOWN
    request = store.mark_completed(request.approval_id, {"executed": True, "reconciled": True})
    assert request.status == ApprovalStatus.COMPLETED


def test_unknown_can_be_reconciled_to_failed() -> None:
    store = ApprovalStore()
    request = store.create(make_request())
    store.decide(ApprovalDecision(approval_id=request.approval_id, approved=True))
    store.mark_executing(request.approval_id)
    store.mark_unknown(request.approval_id, {"error": "timeout"})
    request = store.mark_failed(request.approval_id, {"executed": False, "reconciled": True})
    assert request.status == ApprovalStatus.FAILED


def test_unknown_cannot_be_reexecuted_directly() -> None:
    store = ApprovalStore()
    request = store.create(make_request())
    store.decide(ApprovalDecision(approval_id=request.approval_id, approved=True))
    store.mark_executing(request.approval_id)
    store.mark_unknown(request.approval_id, {"error": "timeout"})
    try:
        store.mark_executing(request.approval_id)
    except InvalidApprovalTransition:
        pass
    else:
        raise AssertionError("Unknown execution was re-executed without reconciliation")
