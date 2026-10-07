import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session", autouse=True)
def ensure_database_schema():
    """Prepare the shared CI PostgreSQL schema before DB-backed tests run."""
    database_url = os.getenv(
        "AI_AUDIT_DATABASE_URL",
        "postgresql+pg8000://mlflow:mlflow@127.0.0.1:55432/mlflow",
    )
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
