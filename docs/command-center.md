# AI Engineering Command Center

The repository includes a lightweight browser dashboard at `ai_engineering/dashboard/index.html`.

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

Serve the dashboard directory from another local process:

```bash
python -m http.server 8088 --directory ai_engineering/dashboard
```

Open `http://127.0.0.1:8088` and enter the API URL, normally `http://127.0.0.1:8010`.

If `AI_ENGINEERING_API_TOKEN` is configured, enter the same token in the dashboard. The browser sends it as a Bearer token.

## Security boundary

The dashboard is read-only. It does not call approval decision, execution or retry mutation endpoints. Infrastructure mutations remain behind the existing human-approval and idempotent execution workflow.

## Production integration

The next integration step is to serve this static asset from the AI Engineering API or a dedicated frontend service. The API contract is intentionally independent of the presentation layer so the UI can evolve without changing the control-plane data model.
