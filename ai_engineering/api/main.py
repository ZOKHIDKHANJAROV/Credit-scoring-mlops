"""FastAPI entrypoint for the AI Engineering Command Center."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.workflows.retraining_workflow import RetrainingWorkflow

app = FastAPI(
    title="AI Engineering Command Center",
    version="0.1.0",
    description="Agentic control plane for the credit-scoring MLOps platform.",
)

approval_store = ApprovalStore()
workflow = RetrainingWorkflow()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-engineering-command-center"}


@app.post("/workflows/retraining/plan")
def create_retraining_plan() -> dict:
    """Build a retraining plan without executing Kubernetes actions."""
    plan = workflow.build_plan()

    response = {
        "status": plan.status,
        "reason": plan.reason,
        "drifted_features": plan.drifted_features,
        "champion": plan.champion,
        "model_comparison": plan.model_comparison,
        "kubernetes_job": plan.kubernetes_job,
    }

    if plan.status == "approval_required":
        approval = approval_store.create(
            ApprovalRequest(
                action="run_model_training",
                reason=plan.reason,
            )
        )
        response["approval"] = approval.model_dump(mode="json")

    return response


@app.get("/approvals")
def list_approvals() -> dict[str, list[dict]]:
    return {
        "items": [item.model_dump(mode="json") for item in approval_store.list_pending()]
    }


@app.post("/approvals/{approval_id}/decide")
def decide_approval(approval_id: str, decision: ApprovalDecision) -> dict:
    if decision.approval_id != approval_id:
        raise HTTPException(status_code=400, detail="approval_id does not match path")

    try:
        request = approval_store.decide(decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return request.model_dump(mode="json")
