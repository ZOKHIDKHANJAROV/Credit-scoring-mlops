from pathlib import Path

import pytest

from ai_engineering.tools.kubernetes_tools import KubernetesTools
from ai_engineering.tools.registry import RegisteredTool, ToolRegistry


def test_registry_rejects_empty_and_duplicate_names() -> None:
    registry = ToolRegistry()
    tool = RegisteredTool(
        name="safe_tool",
        description="test",
        parameters={"type": "object", "properties": {}},
        handler=lambda: {"ok": True},
    )

    registry.register(tool)
    with pytest.raises(ValueError, match="Tool already registered"):
        registry.register(tool)

    with pytest.raises(ValueError, match="Tool name must not be empty"):
        registry.register(
            RegisteredTool(
                name="   ",
                description="invalid",
                parameters={"type": "object"},
                handler=lambda: None,
            )
        )


def test_registry_blocks_approval_required_tools() -> None:
    registry = ToolRegistry(
        [
            RegisteredTool(
                name="mutating_tool",
                description="requires approval",
                parameters={"type": "object", "properties": {}},
                handler=lambda: pytest.fail("handler must not execute"),
                requires_human_approval=True,
            )
        ]
    )

    result = registry.execute("mutating_tool", {})

    assert result["executed"] is False
    assert result["requires_human_approval"] is True
    assert result["tool"] == "mutating_tool"


def test_registry_requires_object_arguments() -> None:
    registry = ToolRegistry(
        [
            RegisteredTool(
                name="safe_tool",
                description="test",
                parameters={"type": "object", "properties": {}},
                handler=lambda: {"ok": True},
            )
        ]
    )

    with pytest.raises(TypeError, match="JSON object"):
        registry.execute("safe_tool", [])  # type: ignore[arg-type]


def test_kubernetes_tool_only_builds_approval_gated_plan(tmp_path: Path) -> None:
    manifest = tmp_path / "model-training-job.yaml"
    manifest.write_text("apiVersion: batch/v1\nkind: Job\n", encoding="utf-8")

    tool = KubernetesTools(manifest_path=manifest)
    result = tool.build_training_job_plan(
        reason="feature drift detected",
        drifted_features=["income", "age"],
    )

    assert result["available"] is True
    assert result["action"] == "create_training_job"
    assert result["requires_human_approval"] is True
    assert result["execution"] == "approval_gated"
    assert result["drifted_features"] == ["income", "age"]


def test_kubernetes_tool_returns_manual_review_when_manifest_missing(tmp_path: Path) -> None:
    tool = KubernetesTools(manifest_path=tmp_path / "missing.yaml")

    result = tool.build_training_job_plan()

    assert result["available"] is False
    assert result["action"] == "manual_review"
    assert result["requires_human_approval"] is True
