"""FastAPI service for the AI Engineering Command Center agent."""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ai_engineering.api.security import api_auth
from ai_engineering.llm.provider import OpenAICompatibleProvider
from ai_engineering.llm.tool_calling import ToolCallingAgent
from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest
from ai_engineering.schemas.audit import AuditEvent, AuditEventType
from ai_engineering.services.audit_service import AuditService
from ai_engineering.services.reconciliation_service import ReconciliationService
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.storage.audit_store import AuditStore
from ai_engineering.tools.default_registry import build_default_registry
from ai_engineering.tools.kubernetes_executor import KubernetesExecutionUnknown, KubernetesExecutor


ALLOWED_MUTATING_ACTIONS = frozenset({"create_training_job"})

app = FastAPI(title="AI Engineering Command Center Agent", version="0.6.0")
approval_store = ApprovalStore()
audit_store = AuditStore()
audit_service = AuditService(audit_store)
kubernetes_executor = KubernetesExecutor()
reconciliation_service = ReconciliationService(approval_store, kubernetes_executor, audit_service)


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


def authenticated(authorization: str | None = Header(default=None)) -> None:
    """Dependency used on every non-health API endpoint."""
    api_auth.require(authorization)


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


@app.get("/api/v1/agent/tools", dependencies=[Depends(authenticated)])
def list_tools() -> dict[str, list[str]]:
    return {"tools": build_default_registry().names()}


@app.post("/api/v1/agent/run", response_model=AgentRunResponse, dependencies=[Depends(authenticated)])
def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    try:
        result = build_agent().run(task=request.task)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Agent execution failed") from exc
    return AgentRunResponse(
        status=str(result.get("status", "unknown")),
        answer=str(result.get("answer", "")),
        tools_used=list(result.get("tools_used", [])),
        trace_id=str(result["trace_id"]),
    )


@app.post("/api/v1/approvals", response_model=ApprovalRequest, status_code=201, dependencies=[Depends(authenticated)])
def create_approval(request: ApprovalCreateRequest) -> ApprovalRequest:
    if request.action not in ALLOWED_MUTATING_ACTIONS:
        raise HTTPException(status_code=400, detail="Unsupported approval action")
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


@app.get("/api/v1/approvals", response_model=list[ApprovalRequest], dependencies=[Depends(authenticated)])
def list_pending_approvals() -> list[ApprovalRequest]:
    return approval_store.list_pending()


@app.get("/api/v1/approvals/{approval_id}", response_model=ApprovalRequest, dependencies=[Depends(authenticated)])
def get_approval(approval_id: str) -> ApprovalRequest:
    approval = approval_store.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.post("/api/v1/approvals/{approval_id}/decision", response_model=ApprovalRequest, dependencies=[Depends(authenticated)])
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


@app.post("/api/v1/approvals/{approval_id}/execute", response_model=ApprovalRequest, dependencies=[Depends(authenticated)])
def execute_approval(approval_id: str) -> ApprovalRequest:
    approval = approval_store.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.action not in ALLOWED_MUTATING_ACTIONS:
        raise HTTPException(status_code=400, detail="Unsupported approval action")
    try:
        approval = approval_store.mark_executing(approval_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit_service.record(AuditEventType.EXECUTION_STARTED, trace_id=approval_id, action=approval.action, status="started")
    try:
        result = kubernetes_executor.apply_training_job(approved=True, execution_id=approval_id)
    except KubernetesExecutionUnknown as exc:
        unknown = approval_store.mark_unknown(approval_id, {"executed": False, "unknown": True, "error": str(exc)})
        audit_service.record(AuditEventType.EXECUTION_UNKNOWN, trace_id=approval_id, action=approval.action, status="unknown", error="execution outcome unknown")
        return unknown
    except Exception as exc:
        failure = {"executed": False, "error": str(exc)}
        approval_store.mark_failed(approval_id, failure)
        audit_service.record(AuditEventType.EXECUTION_FAILED, trace_id=approval_id, action=approval.action, status="failed", error="execution failed", payload={"result": failure})
        raise HTTPException(status_code=500, detail="Execution failed") from exc
    if result.get("executed") is True:
        completed = approval_store.mark_completed(approval_id, result)
        audit_service.record(AuditEventType.EXECUTION_COMPLETED, trace_id=approval_id, action=approval.action, status="completed", payload={"result": result})
        return completed
    failed = approval_store.mark_failed(approval_id, result)
    audit_service.record(AuditEventType.EXECUTION_FAILED, trace_id=approval_id, action=approval.action, status="failed", payload={"result": result})
    return failed


@app.post("/api/v1/approvals/{approval_id}/reconcile", response_model=ApprovalRequest, dependencies=[Depends(authenticated)])
def reconcile_approval(approval_id: str) -> ApprovalRequest:
    try:
        return reconciliation_service.reconcile(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found") from exc
    except KubernetesExecutionUnknown as exc:
        raise HTTPException(status_code=503, detail="Reconciliation outcome is unknown") from exc


@app.get("/api/v1/audit/events", response_model=list[AuditEvent], dependencies=[Depends(authenticated)])
def list_audit_events(
    trace_id: str | None = Query(default=None),
    event_type: AuditEventType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[AuditEvent]:
    try:
        return audit_store.list(trace_id=trace_id, event_type=event_type, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/audit/traces/{trace_id}", response_model=list[AuditEvent], dependencies=[Depends(authenticated)])
def get_trace(trace_id: str) -> list[AuditEvent]:
    return audit_store.list(trace_id=trace_id)


@app.get("/api/v1/audit/stats", dependencies=[Depends(authenticated)])
def audit_stats() -> dict[str, int]:
    return {"event_count": audit_store.count()}
