from __future__ import annotations

from unittest.mock import Mock

from ai_engineering.workflows.model_promotion_workflow import ModelPromotionWorkflow


def evaluation(decision: str, approved: bool) -> dict:
    return {
        "decision": decision,
        "approved": approved,
        "checks": {},
        "failed_checks": [],
    }


def test_promote_requires_human_approval() -> None:
    tools = Mock()
    workflow = ModelPromotionWorkflow(tools)

    result = workflow.execute("7", evaluation("PROMOTE", True), human_approved=False)

    assert result.status == "approval_required"
    tools.promote_model.assert_not_called()


def test_reject_does_not_touch_mlflow() -> None:
    tools = Mock()
    workflow = ModelPromotionWorkflow(tools)

    result = workflow.execute("7", evaluation("REJECT", False), human_approved=True)

    assert result.status == "rejected"
    tools.promote_model.assert_not_called()


def test_manual_review_does_not_touch_mlflow() -> None:
    tools = Mock()
    workflow = ModelPromotionWorkflow(tools)

    result = workflow.execute("7", evaluation("MANUAL_REVIEW", False), human_approved=True)

    assert result.status == "manual_review"
    tools.promote_model.assert_not_called()


def test_invalid_evaluation_cannot_promote() -> None:
    tools = Mock()
    workflow = ModelPromotionWorkflow(tools)

    result = workflow.execute("7", evaluation("PROMOTE", False), human_approved=True)

    assert result.status == "rejected"
    tools.promote_model.assert_not_called()


def test_approved_promotion_is_delegated_to_mlflow() -> None:
    tools = Mock()
    tools.promote_model.return_value = {
        "promoted": True,
        "already_champion": False,
        "model_name": "CreditScoringCatBoost",
        "alias": "champion",
        "version": "7",
        "run_id": "run-7",
    }
    workflow = ModelPromotionWorkflow(tools)

    result = workflow.execute("7", evaluation("PROMOTE", True), human_approved=True)

    assert result.status == "promoted"
    tools.promote_model.assert_called_once_with(
        candidate_version="7",
        decision="PROMOTE",
        human_approved=True,
    )


def test_already_champion_is_idempotent() -> None:
    tools = Mock()
    tools.promote_model.return_value = {
        "promoted": False,
        "already_champion": True,
        "reason": "Model version 7 is already champion",
        "version": "7",
    }
    workflow = ModelPromotionWorkflow(tools)

    result = workflow.execute("7", evaluation("PROMOTE", True), human_approved=True)

    assert result.status == "already_champion"


def test_failed_mlflow_promotion_is_reported() -> None:
    tools = Mock()
    tools.promote_model.return_value = {
        "promoted": False,
        "already_champion": False,
        "reason": "Candidate model version is unavailable",
    }
    workflow = ModelPromotionWorkflow(tools)

    result = workflow.execute("999", evaluation("PROMOTE", True), human_approved=True)

    assert result.status == "failed"
    assert "unavailable" in result.reason
