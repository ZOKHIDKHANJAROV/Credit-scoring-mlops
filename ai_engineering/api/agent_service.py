"""FastAPI service for the AI Engineering Command Center agent."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from ai_engineering.llm.provider import OpenAICompatibleProvider
from ai_engineering.llm.tool_calling import ToolCallingAgent
from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest
from ai_engineering.schemas.audit import AuditEvent, AuditEventType
from ai_engineering.services.audit_service import AuditService
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.storage.audit_store import AuditStore
from ai_engineering.tools.default_registry import build_default_registry
from ai_engineering.tools.kubernetes_executor import KubernetesExecutor


app = FastAPI(
    title="AI Engineering Command Center Agent",
    version="0.3.0",
)

approval_store = ApprovalStore()
audit_store = AuditStore()
audit_service = AuditService(audit_store)
kubernetes_executor = KubernetesExecutor()


class AgentRunRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)


class AgentRunResponse(BaseModel):
    status: str
    answer: str
    tools_used: list[str] = Field(default_factory=list)
    trace_id: str


class ApprovalCreateRequest(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    execution_plan: dict = Field(default_factory=dict)


def build_agent() -> ToolCallingAgent:
    return ToolCallingAgent(
        provider=OpenAICompatibleProvider(),
        registry=build_default_registry(),
        max_rounds=4,
        audit_service=audit_service,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-engineering-agent"}


@app.get("/api/v1/agent/tools")
def list_tools() -> dict[str, list[str]]:
    return {"tools": build_default_registry().names()}


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
        trace_id=str(result["trace_id"]),
    )


@app.post("/api/v1/approvals", response_model=ApprovalRequest, status_code=201)
def create_approval(request: ApprovalCreateRequest) -> ApprovalRequest:
    approval = ApprovalRequest(
        action=request.action,
        reason=request.reason,
        execution_plan=request.execution_plan,
    )
    approval_store.create(approval)
    audit_service.record(
        AuditEventType.APPROVAL_REQUESTED,
        trace_id=approval.approval_id,
        action=approval.action,
        status=approval.status.value,
        payload={"reason": approval.reason, "execution_plan": approval.execution_plan},
    )
    return approval


@app.get("/api/v1/approvals", response_model=list[ApprovalRequest])
def list_pending_approvals() -> list[ApprovalRequest]:
    return approval_store.list_pending()


@app.get("/api/v1/approvals/{approval_id}", response_model=ApprovalRequest)
def get_approval(approval_id: str) -> ApprovalRequest:
    approval = approval_store.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.post("/api/v1/approvals/{approval_id}/decision", response_model=ApprovalRequest)
def decide_approval(approval_id: str, decision: ApprovalDecision) -> ApprovalRequest:
    if decision.approval_id != approval_id:
        raise HTTPException(status_code=400, detail="Approval ID in path and body must match")

    try:
        approval = approval_store.decide(decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    audit_service.record(
        AuditEventType.APPROVAL_DECIDED,
        trace_id=approval_id,
        actor=decision.decided_by,
        action=approval.action,
        status=approval.status.value,
        payload={"approved": decision.approved, "comment": decision.comment},
    )
    return approval


@app.post("/api/v1/approvals/{approval_id}/execute", response_model=ApprovalRequest)
def execute_approval(approval_id: str) -> ApprovalRequest:
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
    audit_service.record(
        AuditEventType.EXECUTION_STARTED,
        trace_id=approval_id,
        action=approval.action,
        status="started",
    )

    try:
        result = kubernetes_executor.apply_training_job(approved=True)
    except Exception as exc:
        failure = {"executed": False, "error": str(exc)}
        approval_store.mark_failed(approval_id, failure)
        audit_service.record(
            AuditEventType.EXECUTION_FAILED,
            trace_id=approval_id,
            action=approval.action,
            status="failed",
            error=str(exc),
            payload={"result": failure},
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if result.get("executed") is True:
        completed = approval_store.mark_completed(approval_id, result)
        audit_service.record(
            AuditEventType.EXECUTION_COMPLETED,
            trace_id=approval_id,
            action=approval.action,
            status="completed",
            payload={"result": result},
        )
        return completed

    failed = approval_store.mark_failed(approval_id, result)
    audit_service.record(
        AuditEventType.EXECUTION_FAILED,
        trace_id=approval_id,
        action=approval.action,
        status="failed",
        payload={"result": result},
    )
    return failed


@app.get("/api/v1/audit/events", response_model=list[AuditEvent])
def list_audit_events(
    trace_id: str | None = Query(default=None),
    event_type: AuditEventType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[AuditEvent]:
    try:
        return audit_store.list(trace_id=trace_id, event_type=event_type, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/audit/traces/{trace_id}", response_model=list[AuditEvent])
def get_trace(trace_id: str) -> list[AuditEvent]:
    return audit_store.list(trace_id=trace_id)


@app.get("/api/v1/audit/stats")
def audit_stats() -> dict[str, int]:
    return {"event_count": audit_store.count()}
