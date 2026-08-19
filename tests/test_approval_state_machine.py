from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus
from ai_engineering.storage.approval_store import ApprovalStore, InvalidApprovalTransition


def make_request() -> ApprovalRequest:
    return ApprovalRequest(action="create_training_job", reason="drift detected")


def test_approval_happy_path() -> None:
    store = ApprovalStore()
    request = store.create(make_request())

    store.decide(ApprovalDecision(approval_id=request.approval_id, approved=True))
    assert request.status == ApprovalStatus.APPROVED

    store.mark_executing(request.approval_id)
    assert request.status == ApprovalStatus.EXECUTING

    store.mark_completed(request.approval_id, {"executed": True})
    assert request.status == ApprovalStatus.COMPLETED


def test_rejection_is_terminal() -> None:
    store = ApprovalStore()
    request = store.create(make_request())
    store.decide(ApprovalDecision(approval_id=request.approval_id, approved=False))

    assert request.status == ApprovalStatus.REJECTED

    try:
        store.mark_executing(request.approval_id)
    except InvalidApprovalTransition:
        pass
    else:
        raise AssertionError("Rejected approval became executable")


def test_completed_is_terminal_and_cannot_be_reexecuted() -> None:
    store = ApprovalStore()
    request = store.create(make_request())
    store.decide(ApprovalDecision(approval_id=request.approval_id, approved=True))
    store.mark_executing(request.approval_id)
    store.mark_completed(request.approval_id, {"executed": True})

    try:
        store.mark_executing(request.approval_id)
    except InvalidApprovalTransition:
        pass
    else:
        raise AssertionError("Completed approval was executed twice")


def test_execution_cannot_complete_or_fail_before_executing() -> None:
    store = ApprovalStore()
    request = store.create(make_request())

    for transition in (
        lambda: store.mark_completed(request.approval_id, {"executed": True}),
        lambda: store.mark_failed(request.approval_id, {"error": "x"}),
    ):
        try:
            transition()
        except InvalidApprovalTransition:
            pass
        else:
            raise AssertionError("Invalid execution transition was accepted")
