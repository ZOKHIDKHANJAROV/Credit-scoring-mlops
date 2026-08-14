"""FastAPI service for the AI Engineering Command Center agent."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_engineering.agents.orchestrator import OrchestratorAgent
from ai_engineering.llm.provider import OpenAICompatibleProvider
from ai_engineering.tools.default_registry import build_default_registry


app = FastAPI(
    title="AI Engineering Command Center Agent",
    version="0.1.0",
)


class AgentRunRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)
    context: dict[str, object] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    status: str
    result: dict[str, object]


def build_orchestrator() -> OrchestratorAgent:
    provider = OpenAICompatibleProvider()
    registry = build_default_registry()
    return OrchestratorAgent(provider=provider, tool_registry=registry)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-engineering-agent"}


@app.post("/api/v1/agent/run", response_model=AgentRunResponse)
def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    try:
        orchestrator = build_orchestrator()
        result = orchestrator.run(task=request.task, context=request.context)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AgentRunResponse(status="completed", result=result)
