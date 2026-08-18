from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalStatus
from ai_engineering.services.model_promotion_service import ModelPromotionApprovalService
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.workflows.model_promotion_workflow import PromotionResult


class FakePromotionWorkflow:
    def __init__(self, status="promoted"):
        self.status = status
        self.calls = []

    def execute(self, candidate_version, evaluation, human_approved):
        self.calls.append((candidate_version, evaluation, human_approved))
        return PromotionResult(
            status=self.status,
            reason="test",
            details={"candidate_version": candidate_version},
        )


def approved_evaluation():
    return {"decision": "PROMOTE", "approved": True}


def test_create_requires_promote_evaluation():
    store = ApprovalStore()
    service = ModelPromotionApprovalService(store, FakePromotionWorkflow())

    try:
        service.create("7", {"decision": "REJECT", "approved": False}, "bad candidate")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "approved PROMOTE" in str(exc)


def test_approved_promotion_executes_workflow():
    store = ApprovalStore()
    workflow = FakePromotionWorkflow()
    service = ModelPromotionApprovalService(store, workflow)

    request = service.create("7", approved_evaluation(), "quality gates passed")
    service.decide(ApprovalDecision(approval_id=request.approval_id, approved=True))
    result = service.execute(request.approval_id)

    assert result.status == ApprovalStatus.COMPLETED
    assert result.execution_result["executed"] is True
    assert workflow.calls[0][0] == "7"
    assert workflow.calls[0][2] is True


def test_rejected_approval_cannot_execute():
    store = ApprovalStore()
    workflow = FakePromotionWorkflow()
    service = ModelPromotionApprovalService(store, workflow)

    request = service.create("7", approved_evaluation(), "quality gates passed")
    service.decide(ApprovalDecision(approval_id=request.approval_id, approved=False))

    try:
        service.execute(request.approval_id)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Only approved requests can execute" in str(exc)
    assert workflow.calls == []


def test_already_champion_is_completed_without_new_promotion():
    store = ApprovalStore()
    workflow = FakePromotionWorkflow(status="already_champion")
    service = ModelPromotionApprovalService(store, workflow)

    request = service.create("7", approved_evaluation(), "quality gates passed")
    service.decide(ApprovalDecision(approval_id=request.approval_id, approved=True))
    result = service.execute(request.approval_id)

    assert result.status == ApprovalStatus.COMPLETED
    assert result.execution_result["status"] == "already_champion"
