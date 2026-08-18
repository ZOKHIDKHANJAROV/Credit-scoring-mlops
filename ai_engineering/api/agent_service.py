"""FastAPI service for the AI Engineering Command Center agent."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_engineering.llm.provider import OpenAICompatibleProvider
from ai_engineering.llm.tool_calling import ToolCallingAgent
from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.tools.default_registry import build_default_registry
from ai_engineering.tools.kubernetes_executor import KubernetesExecutor


app = FastAPI(
    title="AI Engineering Command Center Agent",
    version="0.2.0",
)

approval_store = ApprovalStore()
kubernetes_executor = KubernetesExecutor()


class AgentRunRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)


class AgentRunResponse(BaseModel):
    status: str
    answer: str
    tools_used: list[str] = Field(default_factory=list)


class ApprovalCreateRequest(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    execution_plan: dict = Field(default_factory=dict)


def build_agent() -> ToolCallingAgent:
    provider = OpenAICompatibleProvider()
    registry = build_default_registry()
    return ToolCallingAgent(provider=provider, registry=registry, max_rounds=4)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-engineering-agent"}


@app.get("/api/v1/agent/tools")
def list_tools() -> dict[str, list[str]]:
    registry = build_default_registry()
    return {"tools": registry.names()}


@app.post("/api/v1/agent/run", response_model=AgentRunResponse)
def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    try:
        result = build_agent().run(task=request.task)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AgentRunResponse(
        status=str(result.get("status", "unknown")),
        answer=str(result.get("answer", "")),
        tools_used=list(result.get("tools_used", [])),
    )


@app.post("/api/v1/approvals", response_model=ApprovalRequest, status_code=201)
def create_approval(request: ApprovalCreateRequest) -> ApprovalRequest:
    """Create a pending human-approval request from an agent execution plan."""
    approval = ApprovalRequest(
        action=request.action,
        reason=request.reason,
        execution_plan=request.execution_plan,
    )
    return approval_store.create(approval)


@app.get("/api/v1/approvals", response_model=list[ApprovalRequest])
def list_pending_approvals() -> list[ApprovalRequest]:
    """Return approvals that still require a human decision."""
    return approval_store.list_pending()


@app.get("/api/v1/approvals/{approval_id}", response_model=ApprovalRequest)
def get_approval(approval_id: str) -> ApprovalRequest:
    approval = approval_store.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.post("/api/v1/approvals/{approval_id}/decision", response_model=ApprovalRequest)
def decide_approval(approval_id: str, decision: ApprovalDecision) -> ApprovalRequest:
    """Approve or reject a pending request. The path ID is authoritative."""
    if decision.approval_id != approval_id:
        raise HTTPException(status_code=400, detail="Approval ID in path and body must match")

    try:
        return approval_store.decide(decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/v1/approvals/{approval_id}/execute", response_model=ApprovalRequest)
def execute_approval(approval_id: str) -> ApprovalRequest:
    """Execute an approved, allowlisted action and persist its result."""
    approval = approval_store.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status.value != "approved":
        raise HTTPException(
            status_code=409,
            detail=f"Only approved requests can execute; current status is {approval.status.value}",
        )
    if approval.action != "create_training_job":
        raise HTTPException(status_code=400, detail=f"Unsupported approval action: {approval.action}")

    approval_store.mark_executing(approval_id)
    try:
        result = kubernetes_executor.apply_training_job(approved=True)
    except Exception as exc:
        approval_store.mark_failed(
            approval_id,
            {"executed": False, "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if result.get("executed") is True:
        return approval_store.mark_completed(approval_id, result)

    return approval_store.mark_failed(approval_id, result)
