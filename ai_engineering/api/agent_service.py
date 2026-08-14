"""FastAPI service for the AI Engineering Command Center agent."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_engineering.llm.provider import OpenAICompatibleProvider
from ai_engineering.llm.tool_calling import ToolCallingAgent
from ai_engineering.tools.default_registry import build_default_registry


app = FastAPI(
    title="AI Engineering Command Center Agent",
    version="0.1.0",
)


class AgentRunRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)


class AgentRunResponse(BaseModel):
    status: str
    answer: str
    tools_used: list[str] = Field(default_factory=list)


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
