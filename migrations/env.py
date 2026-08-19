"""Alembic migration environment for AI Engineering persistence."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from ai_engineering.storage.audit_store import Base as AuditBase
from ai_engineering.storage.approval_store import Base as ApprovalBase

config = context.config
if os.getenv("AI_AUDIT_DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.environ["AI_AUDIT_DATABASE_URL"])
elif os.getenv("MONITORING_DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.environ["MONITORING_DATABASE_URL"])

target_metadata = [AuditBase.metadata, ApprovalBase.metadata]


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
