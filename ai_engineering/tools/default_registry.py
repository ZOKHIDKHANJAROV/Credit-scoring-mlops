"""Default safe tools exposed to the AI Engineering orchestrator."""

from __future__ import annotations

from ai_engineering.tools.mlflow_tools import MLflowTools
from ai_engineering.tools.monitoring_tools import MonitoringTools
from ai_engineering.tools.registry import RegisteredTool, ToolRegistry


def build_default_registry(
    monitoring_tools: MonitoringTools | None = None,
    mlflow_tools: MLflowTools | None = None,
) -> ToolRegistry:
    """Build the initial read-only tool registry."""
    monitoring = monitoring_tools or MonitoringTools()
    mlflow = mlflow_tools or MLflowTools()

    return ToolRegistry(
        [
            RegisteredTool(
                name="monitoring_get_retrain_signal",
                description="Read the current Evidently retraining signal. Read-only.",
                parameters={"type": "object", "properties": {}, "additionalProperties": False},
                handler=monitoring.get_retrain_signal,
            ),
            RegisteredTool(
                name="mlflow_get_champion_model",
                description="Read the current champion model metadata from MLflow. Read-only.",
                parameters={"type": "object", "properties": {}, "additionalProperties": False},
                handler=mlflow.get_champion_model,
            ),
            RegisteredTool(
                name="mlflow_compare_latest_models",
                description="Compare the latest CatBoost, LightGBM and XGBoost runs in MLflow. Read-only.",
                parameters={"type": "object", "properties": {}, "additionalProperties": False},
                handler=mlflow.compare_latest_models,
            ),
        ]
    )
