"""Schemas for post-training model review decisions."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ModelReview(BaseModel):
    status: ReviewStatus
    reason: str
    champion_roc_auc: float | None = None
    candidate_roc_auc: float | None = None
    min_roc_auc_improvement: float = Field(default=0.0, ge=0.0)
