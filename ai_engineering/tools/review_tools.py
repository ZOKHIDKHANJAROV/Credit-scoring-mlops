"""Tool wrapper around the deterministic model reviewer."""

from __future__ import annotations

from typing import Any

from ai_engineering.agents.reviewer_agent import QualityGateConfig, ReviewerAgent


class ReviewTools:
    def __init__(self) -> None:
        self.reviewer = ReviewerAgent(QualityGateConfig())

    def review_candidate(
        self,
        champion: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        return self.reviewer.review(champion=champion, candidate=candidate)
