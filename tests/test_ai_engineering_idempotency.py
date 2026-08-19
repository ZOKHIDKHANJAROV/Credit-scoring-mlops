from concurrent.futures import ThreadPoolExecutor

import pytest

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus
from ai_engineering.storage.approval_store import ApprovalStore, InvalidApprovalTransition


def make_approved(store: ApprovalStore) -> ApprovalRequest:
    request = store.create(
        ApprovalRequest(
            action="create_training_job",
            reason="Drift threshold exceeded",
            execution_plan={"job": "credit-model-training"},
        )
    )
    return store.decide(
        ApprovalDecision(
            approval_id=request.approval_id,
            approved=True,
            decided_by="test",
        )
    )


def test_execution_transition_is_single_use() -> None:
    store = ApprovalStore()
    request = make_approved(store)

    store.mark_executing(request.approval_id)

    with pytest.raises(InvalidApprovalTransition):
        store.mark_executing(request.approval_id)


def test_completed_is_terminal() -> None:
    store = ApprovalStore()
    request = make_approved(store)

    store.mark_executing(request.approval_id)
    store.mark_completed(request.approval_id, {"executed": True})

    assert store.get(request.approval_id).status == ApprovalStatus.COMPLETED
    with pytest.raises(InvalidApprovalTransition):
        store.mark_executing(request.approval_id)


def test_concurrent_execution_allows_only_one_transition() -> None:
    store = ApprovalStore()
    request = make_approved(store)

    def try_execute() -> str:
        try:
            store.mark_executing(request.approval_id)
            return "executing"
        except InvalidApprovalTransition:
            return "rejected"

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: try_execute(), range(8)))

    assert results.count("executing") == 1
    assert results.count("rejected") == 7
    assert store.get(request.approval_id).status == ApprovalStatus.EXECUTING
