# AI Engineering Command Center

The repository includes a lightweight read-only browser dashboard at `ai_engineering/dashboard/index.html`.

## Backend contract

The dashboard consumes the read-only endpoint:

```http
GET /api/v1/command-center/overview
```

The endpoint provides approval state counts, audit event counts, pending approvals, reconcilable executions, recent approvals and recent audit events.

## Local development

Start the AI Engineering API:

```bash
uvicorn ai_engineering.api.agent_service:app --host 0.0.0.0 --port 8010
```

Open the dashboard from the same API origin:

```text
http://127.0.0.1:8010/command-center/
```

The dashboard defaults to the current browser origin, so no separate static server or CORS configuration is required. If `AI_ENGINEERING_API_TOKEN` is configured, enter the same token in the dashboard. The browser sends it as a Bearer token.

The previous standalone static-server workflow is no longer required. The FastAPI service mounts the repository dashboard directly under `/command-center`.

## Security boundary

The dashboard is read-only. It does not call approval decision, execution or retry mutation endpoints. Infrastructure mutations remain behind the existing human-approval and idempotent execution workflow.

## Production integration

The dashboard is served by the same FastAPI process, which keeps browser/API traffic same-origin and avoids a permissive CORS policy. The API contract remains independent of the presentation layer so the UI can evolve without changing the control-plane data model.
