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
