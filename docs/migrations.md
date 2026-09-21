# Database migrations

AI Engineering persistence is managed with Alembic.

## Local validation

Set `AI_AUDIT_DATABASE_URL` and run:

```bash
alembic upgrade head
alembic current
pytest -q tests/test_alembic_migrations.py
```

The CI migration smoke test runs `upgrade head` against a clean PostgreSQL service and verifies the schema and final revision. This catches missing or inconsistent migrations before deployment.


## Runtime behavior

The FastAPI Command Center and reconciliation worker start with `auto_create=False` for AI Engineering persistence. Runtime startup does not create or mutate the control-plane schema.

Deployments must apply Alembic migrations before starting the API or reconciliation worker:

```bash
alembic upgrade head
```

The store-level `auto_create` option remains available for isolated test fixtures and explicit development tooling, but production entrypoints do not use it.
