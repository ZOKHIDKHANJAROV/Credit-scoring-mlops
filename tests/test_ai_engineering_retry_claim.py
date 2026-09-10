from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus
from ai_engineering.storage.approval_store import ApprovalStore


def test_retry_claim_has_single_owner() -> None:
    store = ApprovalStore()
    store.clear()

    request = store.create(
        ApprovalRequest(action="create_training_job", reason="atomic retry claim")
    )
    store.decide(
        ApprovalDecision(approval_id=request.approval_id, approved=True, decided_by="test")
    )
    store.mark_executing(request.approval_id)
    store.mark_unknown(request.approval_id, {"unknown": True})

    first, first_owner = store.claim_retry_execution(request.approval_id)
    second, second_owner = store.claim_retry_execution(request.approval_id)

    assert first_owner is True
    assert first.status == ApprovalStatus.EXECUTING
    assert second_owner is False
    assert second.status == ApprovalStatus.EXECUTING

    store.clear()
