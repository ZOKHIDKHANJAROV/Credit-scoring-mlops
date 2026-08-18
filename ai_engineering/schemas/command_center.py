"""API schemas for the AI Engineering Command Center orchestrator."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CommandCenterRunRequest(BaseModel):
    """User request passed to the deterministic command-center pipeline."""

    task: str = Field(default="auto", min_length=1, max_length=4000)


class CommandCenterRunResponse(BaseModel):
    """Structured orchestration result returned by the API."""

    status: str
    action: str
    reason: str
    requires_human_approval: bool
    stages: list[str] = Field(default_factory=list)
    data: dict = Field(default_factory=dict)
