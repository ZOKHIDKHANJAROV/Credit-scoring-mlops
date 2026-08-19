-- PostgreSQL reference schema for the AI Engineering Command Center audit log.
-- The application creates the same table automatically through SQLAlchemy.

CREATE TABLE IF NOT EXISTS ai_engineering_audit_events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL UNIQUE,
    event_type VARCHAR(64) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    trace_id VARCHAR(36) NOT NULL,
    actor VARCHAR(128) NOT NULL,
    action VARCHAR(128),
    tool_name VARCHAR(128),
    status VARCHAR(64),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT
);

CREATE INDEX IF NOT EXISTS ix_ai_engineering_audit_events_trace_id
    ON ai_engineering_audit_events (trace_id);
CREATE INDEX IF NOT EXISTS ix_ai_engineering_audit_events_event_type
    ON ai_engineering_audit_events (event_type);
CREATE INDEX IF NOT EXISTS ix_ai_engineering_audit_events_occurred_at
    ON ai_engineering_audit_events (occurred_at DESC);
