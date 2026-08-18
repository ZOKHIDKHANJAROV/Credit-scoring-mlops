# AI Engineering Audit Persistence

The command center audit log is persisted in PostgreSQL through SQLAlchemy.

## Configuration

Set `AI_AUDIT_DATABASE_URL` to a SQLAlchemy database URL. If it is not set, the service falls back to `MONITORING_DATABASE_URL`, then to the local MLflow PostgreSQL URL:

```text
AI_AUDIT_DATABASE_URL=postgresql+pg8000://mlflow:mlflow@127.0.0.1:55432/mlflow
```

The audit store creates `ai_engineering_audit_events` automatically on startup. A reference SQL schema is available in `ai_engineering/storage/audit_schema.sql`.

## Stored fields

- `event_id`: globally unique event identifier
- `event_type`: agent/tool/approval/execution lifecycle event
- `occurred_at`: UTC event timestamp
- `trace_id`: correlation identifier for one execution lifecycle
- `actor`: component that produced the event
- `action`: optional infrastructure/model action
- `tool_name`: optional allowlisted tool name
- `status`: lifecycle status
- `payload`: structured JSON payload
- `error`: optional error text

## API

The existing audit endpoints continue to expose the same Pydantic `AuditEvent` schema:

- `GET /api/v1/audit/events`
- `GET /api/v1/audit/traces/{trace_id}`
- `GET /api/v1/audit/stats`

No GPU or Kubernetes execution is required to use the persistence layer.
