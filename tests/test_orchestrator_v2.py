from __future__ import annotations

from dataclasses import dataclass

from ai_engineering.agents.orchestrator_v2 import CommandCenterOrchestrator


@dataclass
class FakeMonitoring:
    signal: dict

    def get_retrain_signal(self) -> dict:
        return self.signal


@dataclass
class FakeMLAgent:
    evaluation: dict

    def evaluate(self) -> dict:
        return self.evaluation


@dataclass
class FakeKubernetes:
    plan: dict

    def get_training_job_plan(self) -> dict:
        return self.plan


def test_no_drift_stops_pipeline_without_approval() -> None:
    orchestrator = CommandCenterOrchestrator(
        monitoring=FakeMonitoring({
            "available": True,
            "retrain_required": False,
            "reason": "No significant drift",
            "drifted_features": [],
        }),
        ml_agent=FakeMLAgent({"decision": "PROMOTE", "reason": "unused"}),
        kubernetes=FakeKubernetes({"available": True}),
    )

    result = orchestrator.run()

    assert result.status == "completed"
    assert result.action == "no_action"
    assert result.requires_human_approval is False
    assert result.stages == ["monitoring"]


def test_drift_and_rejected_candidate_stop_without_mutation() -> None:
    orchestrator = CommandCenterOrchestrator(
        monitoring=FakeMonitoring({
            "available": True,
            "retrain_required": True,
            "reason": "Feature drift detected",
            "drifted_features": ["income"],
        }),
        ml_agent=FakeMLAgent({"decision": "REJECT", "reason": "Quality gates failed"}),
        kubernetes=FakeKubernetes({"available": True}),
    )

    result = orchestrator.run()

    assert result.status == "completed"
    assert result.action == "no_action"
    assert result.requires_human_approval is False
    assert result.stages == ["monitoring", "evaluation"]


def test_drift_and_manual_review_require_human_approval() -> None:
    orchestrator = CommandCenterOrchestrator(
        monitoring=FakeMonitoring({
            "available": True,
            "retrain_required": True,
            "reason": "Feature drift detected",
            "drifted_features": ["income"],
        }),
        ml_agent=FakeMLAgent({
            "decision": "MANUAL_REVIEW",
            "reason": "Champion metrics unavailable",
        }),
        kubernetes=FakeKubernetes({"available": True}),
    )

    result = orchestrator.run()

    assert result.status == "manual_review"
    assert result.action == "request_human_approval"
    assert result.requires_human_approval is True
    assert result.stages == ["monitoring", "evaluation"]


def test_successful_pipeline_creates_only_an_approval_plan() -> None:
    orchestrator = CommandCenterOrchestrator(
        monitoring=FakeMonitoring({
            "available": True,
            "retrain_required": True,
            "reason": "Feature drift detected",
            "drifted_features": ["income", "age"],
        }),
        ml_agent=FakeMLAgent({
            "decision": "PROMOTE",
            "reason": "All quality gates passed",
        }),
        kubernetes=FakeKubernetes({
            "available": True,
            "action": "create_training_job",
            "requires_human_approval": True,
        }),
    )

    result = orchestrator.run()

    assert result.status == "approval_required"
    assert result.action == "create_training_job"
    assert result.requires_human_approval is True
    assert result.stages == ["monitoring", "evaluation", "reviewer", "approval"]
    assert result.data["kubernetes_job"]["requires_human_approval"] is True


def test_missing_monitoring_signal_fails_closed() -> None:
    orchestrator = CommandCenterOrchestrator(
        monitoring=FakeMonitoring({
            "available": False,
            "retrain_required": False,
            "reason": "Signal unavailable",
            "drifted_features": [],
        }),
        ml_agent=FakeMLAgent({"decision": "PROMOTE"}),
        kubernetes=FakeKubernetes({"available": True}),
    )

    result = orchestrator.run()

    assert result.status == "manual_review"
    assert result.action == "request_human_approval"
    assert result.requires_human_approval is True
    assert result.stages == ["monitoring"]
