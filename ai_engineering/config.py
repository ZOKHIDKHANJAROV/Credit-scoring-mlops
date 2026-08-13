"""Configuration for the AI Engineering Command Center."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Runtime configuration shared by agents and tools."""

    llm_provider: str = os.getenv("AI_LLM_PROVIDER", "ollama")
    llm_model: str = os.getenv("AI_LLM_MODEL", "qwen3:8b")
    mlflow_tracking_uri: str = os.getenv(
        "MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"
    )
    monitoring_database_url: str = os.getenv(
        "MONITORING_DATABASE_URL",
        "postgresql+pg8000://mlflow:mlflow@127.0.0.1:55432/mlflow",
    )
    agent_mode: str = os.getenv("AI_AGENT_MODE", "safe")


settings = Settings()
