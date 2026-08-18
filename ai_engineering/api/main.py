"""FastAPI entrypoint for the AI Engineering Command Center."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ai_engineering.agents.orchestrator_v2 import CommandCenterOrchestrator
from ai_engineering.schemas.approvals import ApprovalDecision
from ai_engineering.schemas.command_center import CommandCenterRunRequest, CommandCenterRunResponse
from ai_engineering.services.approval_service import ApprovalService
from ai_engineering.services.model_promotion_service import ModelPromotionApprovalService
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.tools.kubernetes_executor import KubernetesExecutor
from ai_engineering.workflows.model_promotion_workflow import ModelPromotionWorkflow
from ai_engineering.workflows.retraining_workflow import RetrainingWorkflow

app = FastAPI(
    title="AI Engineering Command Center",
    version="0.4.0",
    description="Agentic control plane for the credit-scoring MLOps platform.",
)

approval_store = ApprovalStore()
workflow = RetrainingWorkflow()
approval_service = ApprovalService(store=approval_store, executor=KubernetesExecutor())
promotion_service = ModelPromotionApprovalService(store=approval_store, workflow=ModelPromotionWorkflow())
command_center = CommandCenterOrchestrator()
DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "ui" / "index.html"


class PromotionPlanRequest(BaseModel):
    candidate_version: str = Field(min_length=1, max_length=100)
    evaluation: dict[str, Any]
    reason: str = Field(min_length=1, max_length=2000)


def _create_training_approval_if_needed(
    action: str,
    reason: str,
    execution_plan: dict[str, Any],
) -> dict[str, Any]:
    if action != "create_training_job":
        raise ValueError(f"Unsupported approval action: {action}")
    return approval_service.create_training_approval(
        reason=reason,
        execution_plan=execution_plan,
    ).model_dump(mode="json")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(DASHBOARD_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-engineering-command-center"}


@app.post("/api/v1/command-center/run", response_model=CommandCenterRunResponse)
def run_command_center(request: CommandCenterRunRequest) -> CommandCenterRunResponse:
    try:
        result = command_center.run(request.task)
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response = CommandCenterRunResponse(
        status=result.status,
        action=result.action,
        reason=result.reason,
        requires_human_approval=result.requires_human_approval,
        stages=result.stages,
        data=result.data,
    )

    if result.action == "create_training_job" and result.status == "approval_required":
        response.data["approval"] = _create_training_approval_if_needed(
            action=result.action,
            reason=result.reason,
            execution_plan=result.data.get("kubernetes_job", {}),
        )

    return response


@app.post("/workflows/retraining/plan")
def create_retraining_plan() -> dict[str, Any]:
    plan = workflow.build_plan()
    response: dict[str, Any] = {
        "status": plan.status,
        "reason": plan.reason,
        "drifted_features": plan.drifted_features,
        "champion": plan.champion,
        "model_comparison": plan.model_comparison,
        "kubernetes_job": plan.kubernetes_job,
    }
    if plan.status == "approval_required":
        response["approval"] = _create_training_approval_if_needed(
            action="create_training_job",
            reason=plan.reason,
            execution_plan=plan.kubernetes_job or {},
        )
    return response


@app.post("/workflows/model-promotion/plan")
def create_model_promotion_plan(request: PromotionPlanRequest) -> dict[str, Any]:
    try:
        approval = promotion_service.create(
            candidate_version=request.candidate_version,
            evaluation=request.evaluation,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "approval_required", "approval": approval.model_dump(mode="json")}


@app.get("/approvals")
def list_approvals() -> dict[str, list[dict[str, Any]]]:
    return {"items": [item.model_dump(mode="json") for item in approval_store.list_all()]}


@app.post("/approvals/{approval_id}/decide")
def decide_approval(approval_id: str, decision: ApprovalDecision) -> dict[str, Any]:
    if decision.approval_id != approval_id:
        raise HTTPException(status_code=400, detail="approval_id does not match path")
    try:
        request = approval_store.get(approval_id)
        if request is None:
            raise KeyError(f"Approval not found: {approval_id}")
        if request.action == ModelPromotionApprovalService.ACTION:
            request = promotion_service.decide(decision)
        else:
            request = approval_service.decide(decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return request.model_dump(mode="json")


@app.post("/approvals/{approval_id}/execute")
def execute_approval(approval_id: str) -> dict[str, Any]:
    request = approval_store.get(approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    try:
        if request.action == ModelPromotionApprovalService.ACTION:
            result = promotion_service.execute(approval_id)
        elif request.action == "create_training_job":
            result = approval_service.execute(approval_id)
        else:
            raise ValueError(f"Unsupported approval action: {request.action}")
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@app.post("/approvals/{approval_id}/refresh")
def refresh_approval(approval_id: str) -> dict[str, Any]:
    """Poll the external execution state and update the approval lifecycle."""
    request = approval_store.get(approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    if request.action != "create_training_job":
        raise HTTPException(status_code=409, detail="Only training-job approvals support refresh")
    try:
        result = approval_service.refresh_execution(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.model_dump(mode="json")
