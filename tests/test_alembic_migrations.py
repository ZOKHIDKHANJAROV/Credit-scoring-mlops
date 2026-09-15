import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_alembic_upgrade_head_creates_current_schema():
    database_url = os.getenv(
        "AI_AUDIT_DATABASE_URL",
        "postgresql+pg8000://mlflow:mlflow@127.0.0.1:55432/mlflow",
    )

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        approval_names = {column["name"] for column in inspector.get_columns("ai_engineering_approvals")}
        audit_names = {column["name"] for column in inspector.get_columns("ai_engineering_audit_events")}

        assert {"approval_id", "trace_id", "execution_started_at", "status"} <= approval_names
        assert {"event_id", "trace_id", "event_type", "payload"} <= audit_names

        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision == "20260910_0003"
    finally:
        engine.dispose()
