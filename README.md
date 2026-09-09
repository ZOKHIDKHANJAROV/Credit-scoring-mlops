# Credit Scoring MLOps + AI Engineering Command Center

Production-oriented MLOps platform for credit default prediction with an AI Engineering Command Center that can inspect model health, evaluate candidates, coordinate approvals, trace agent execution, and prepare controlled Kubernetes actions.

The project combines a classical ML production pipeline with an agentic engineering control plane. The AI layer is deliberately bounded: tools are allowlisted, mutating infrastructure actions require human approval, and execution state is persisted so repeated requests do not accidentally execute the same operation twice.

> **Status:** active engineering project. The GPU-backed Kubernetes runtime is optional for development. Core application logic and tests are designed to run without a GPU.

---

## What this project demonstrates

### MLOps platform

- Data validation and feature engineering
- DVC pipeline orchestration
- CatBoost, LightGBM and XGBoost training
- MLflow experiment tracking and Model Registry
- Champion model promotion
- FastAPI online scoring
- PostgreSQL scoring logs
- SHAP explanations
- Evidently drift detection and retraining signals
- Prometheus metrics and Grafana dashboards
- Airflow batch and retraining workflows
- Redpanda/Kafka real-time scoring
- Docker Compose infrastructure
- Pytest and GitHub Actions CI

### AI Engineering Command Center

- Bounded LLM tool-calling agent
- Allowlisted read-only MLflow and monitoring tools
- Structured engineering decisions
- Reviewer/quality-gate workflow
- Human approval for mutating actions
- Kubernetes training-job planning and approval-gated execution
- Agent execution tracing with `trace_id`
- Audit events for agent/tool execution
- PostgreSQL persistence for approvals and audit events
- Idempotent approval/execution state transitions
- Alembic database migrations
- FastAPI endpoints for agent, approval and audit workflows

---

## High-level architecture

```text
                         CREDIT SCORING MLOPS PLATFORM

 Raw Data
    │
    ▼
Data Validation ──► Feature Engineering
                         │
                         ▼
                Model Training
             ┌────────┬────────┐
             ▼        ▼        ▼
         CatBoost  LightGBM  XGBoost
             └────────┬────────┘
                      ▼
              MLflow Tracking
                      │
                      ▼
               Model Registry
                      │
                      ▼
             Champion Model
                 @champion
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
     FastAPI API            Redpanda/Kafka
          │                       │
          └───────────┬───────────┘
                      ▼
                PostgreSQL
                      │
             ┌────────┴────────┐
             ▼                 ▼
        Observability      Scoring Logs
             │
      Prometheus/Grafana


                     AI ENGINEERING COMMAND CENTER

             Monitoring / MLflow / Model Signals
                         │
                         ▼
                  Orchestrator Agent
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Read-only tools        LLM reasoning
              │                     │
              └──────────┬──────────┘
                         ▼
                    Decision
                         │
                ┌────────┴────────┐
                │                 │
          no mutation       mutation required
                │                 │
                ▼                 ▼
             result          Human Approval
                                  │
                                  ▼
                         PostgreSQL State
                                  │
                           Idempotent Guard
                                  │
                                  ▼
                         Kubernetes Executor
                                  │
                                  ▼
                           Training Job

Every agent/tool execution can carry a trace ID and produce an audit event.
```

---

## AI Engineering safety model

The agent is not a general-purpose shell with an LLM taped to it. Tools are explicitly registered and executed through an allowlist.

```text
LLM
 │
 ▼
Tool Registry
 │
 ├── monitoring_get_retrain_signal       read-only
 ├── mlflow_get_champion_model           read-only
 ├── mlflow_compare_latest_models        read-only
 └── Kubernetes training action         approval-gated

Mutation path:

request
  ↓
plan
  ↓
human approval
  ↓
atomic state transition
  ↓
idempotency check
  ↓
execution
  ↓
audit event
```

The system is designed so an LLM cannot directly issue arbitrary `kubectl`, database, shell, or infrastructure commands.

---

## Approval state machine

Approval records use an explicit state machine:

```text
                 ┌──────────────┐
                 │    PENDING   │
                 └──────┬───────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
          APPROVED             REJECTED
              │
              ▼
          EXECUTING
          │       │
          ▼       ▼
     COMPLETED   FAILED
```

Execution is guarded by a database-backed state transition so two concurrent requests cannot both move the same approval into execution.

---

## Persistence and idempotency

The AI Engineering layer uses PostgreSQL for durable control-plane state.

### Approval persistence

Stores approval requests, status, timestamps, decision metadata and execution information.

### Audit persistence

Stores agent/tool events including:

- event ID
- event type
- timestamp
- trace ID
- actor
- action
- tool name
- status
- structured payload
- error information

### Migrations

Database schema changes are managed with Alembic:

```text
alembic.ini
migrations/
├── env.py
├── script.py.mako
└── versions/
    └── 20260819_0001_ai_engineering_persistence.py
```

Typical migration commands:

```bash
alembic upgrade head
alembic current
alembic history
```

Production schema evolution should go through migrations rather than relying on application startup to create tables.

---

## Main repository structure

```text
Credit-scoring-mlops/
│
├── ai_engineering/
│   ├── agents/              # agent roles and orchestration
│   ├── api/                 # AI Engineering FastAPI service
│   ├── llm/                 # provider and tool-calling loop
│   ├── policies/            # model/action policies
│   ├── schemas/             # typed domain contracts
│   ├── services/            # audit and execution services
│   ├── storage/             # approval/audit persistence
│   ├── tools/               # allowlisted engineering tools
│   └── workflows/           # controlled engineering workflows
│
├── migrations/              # Alembic migrations
├── docs/                    # engineering architecture notes
│
├── configs/                 # feature configuration
├── dags/                    # Airflow pipelines
├── monitoring/              # Prometheus/Grafana configuration
├── scripts/                 # operational and Kafka scripts
├── services/                # credit scoring API and consumer
├── src/                     # ML/data/training/monitoring code
├── tests/                   # unit and integration-oriented tests
│
├── k8s/                     # Kubernetes manifests
├── docker-compose.yml       # local infrastructure
├── Dockerfile               # scoring service image
├── requirements.txt
├── requirements-airflow.txt
├── requirements-kafka.txt
├── dvc.yaml
├── dvc.lock
├── pytest.ini
└── README.md
```

---

## AI Engineering API

The AI Engineering service exposes the control-plane API.

### Health

```http
GET /health
```

### Registered tools

```http
GET /api/v1/agent/tools
```

### Run the agent

```http
POST /api/v1/agent/run
Content-Type: application/json
```

Example request:

```json
{
  "task": "Check whether the current model should be retrained."
}
```

The agent returns a structured response containing status, final answer and tools used.

Mutating workflows are designed to stop at the approval boundary rather than silently executing infrastructure changes.

---

## Core ML workflow

```text
validate_data
      ↓
build_features
      ↓
train_catboost ─┐
train_lightgbm ─┼─► select_best_model
train_xgboost ─┘          │
                           ▼
                    promote_model
                           │
                           ▼
                    MLflow champion
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
            online scoring      monitoring
                                     │
                                     ▼
                              retrain signal
```

Run the DVC pipeline:

```bash
dvc repro
```

Run a specific stage:

```bash
dvc repro train_catboost
```

---

## Model results

Current reference results from the project benchmark:

| Model | ROC-AUC | Gini | Accuracy | F1 |
|---|---:|---:|---:|---:|
| CatBoost | 0.8139 | 0.6279 | 0.7400 | 0.6232 |
| LightGBM | 0.7669 | 0.5338 | 0.7150 | 0.5649 |
| XGBoost | 0.8038 | 0.6076 | 0.7650 | 0.6179 |

Champion model:

```text
CreditScoringCatBoost@champion
```

These numbers are reference benchmark results, not a guarantee of current production performance. Production decisions should be based on the metrics recorded in MLflow for the deployed model version.

---

## Observability

The base scoring platform exposes Prometheus metrics such as:

```text
credit_scoring_requests_total
credit_scoring_errors_total
credit_scoring_request_latency_seconds
credit_scoring_decision_total
credit_scoring_risk_level_total
credit_scoring_retrain_required
```

The AI Engineering layer additionally records execution traces and audit events.

Conceptually:

```text
request
  ↓
trace_id
  ├── agent decision
  ├── tool call
  ├── tool result
  ├── approval event
  └── execution result
```

This gives the system a durable explanation of what an agent did, which tools it used, and what happened at the approval/execution boundary.

---

## Testing

The repository contains tests for both the scoring platform and AI Engineering layer, including:

- scoring behavior
- agent tool registry
- audit event handling
- execution tracing
- approval state transitions
- idempotency behavior
- trace API
- PostgreSQL-oriented audit storage

Run tests locally:

```bash
pytest -v
```

The PostgreSQL-oriented tests are designed so the core unit-test suite does not require a GPU or a live Kubernetes cluster. Infrastructure-backed integration tests can be added separately when the corresponding services are available.

---

## CI/CD

GitHub Actions is used to validate the repository.

Expected CI flow:

```text
checkout
   ↓
install dependencies
   ↓
pytest
```

The project should keep CI dependency installation aligned with `requirements.txt` so newly added AI Engineering components are tested in the same environment as local development.

---

## Local development

The core AI Engineering code can be developed without GPU execution.

Create a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest -v
```

Run the AI Engineering API during local development:

```bash
uvicorn ai_engineering.api.agent_service:app --host 0.0.0.0 --port 8010
```

Then open:

```text
http://127.0.0.1:8010/docs
```

LLM tool calling uses an OpenAI-compatible endpoint. For a local vLLM deployment, configure for example:

```text
LLM_BASE_URL=http://localhost:8000/v1
LLM_API_KEY=local
LLM_MODEL=Qwen/Qwen3-8B
```

The LLM runtime is optional for unit tests that exercise deterministic components.

---

## Docker Compose infrastructure

The main platform can be started with:

```bash
docker compose up -d --build
```

Typical local services include:

| Service | Address |
|---|---|
| FastAPI scoring API | `127.0.0.1:8000` |
| AI Engineering API | `127.0.0.1:8010` |
| MLflow | `127.0.0.1:5000` |
| Prometheus | `127.0.0.1:9090` |
| Grafana | `127.0.0.1:3000` |
| Airflow | `127.0.0.1:8080` |
| Kafka UI | `127.0.0.1:8081` |
| PostgreSQL | `127.0.0.1:55432` |

Actual exposed ports should be treated as environment/configuration rather than hard-coded production contracts.

---

## Kubernetes

Kubernetes manifests are used for controlled AI Engineering workloads.

The important security boundary is:

```text
LLM
 ↓
training job plan
 ↓
human approval
 ↓
Kubernetes executor
 ↓
Job
```

The agent does not receive arbitrary cluster administration capabilities.

A local `kind` cluster can be used for development and integration testing. GPU support is not required for validating the control-plane logic.

---

## Engineering roadmap

The project is being developed in milestones:

### Completed foundation

- Credit scoring ML pipeline
- MLflow model lifecycle
- FastAPI scoring
- Kafka/Redpanda scoring
- Monitoring and drift detection
- AI Engineering agent/tool-calling foundation
- Approval workflow
- Kubernetes action boundary
- Agent audit/tracing
- PostgreSQL persistence foundation

### Current milestone

**Persistent and idempotent AI Engineering control plane**

- durable approval state
- durable audit events
- idempotent execution
- Alembic migrations
- stronger CI validation
- concurrency/state-machine tests

### Next milestone

**Command Center UI and production hardening**

- dashboard against the final backend contracts
- end-to-end approval flow
- richer observability
- security hardening
- deployment documentation
- release automation

---

## Project principles

1. **Read-only by default.**
2. **Mutations require explicit human approval.**
3. **Every important agent execution should be traceable.**
4. **Approval and execution state must be durable.**
5. **Repeated requests must not duplicate destructive work.**
6. **Infrastructure execution is separated from LLM reasoning.**
7. **Tests must cover state transitions, not just happy-path endpoints.**
8. **Production schema changes are migration-driven.**
9. **GPU and Kubernetes are optional dependencies for core development.**

---

## Portfolio value

This repository demonstrates more than model training. It covers the engineering lifecycle around a production ML system:

```text
ML
├── training
├── evaluation
├── registry
└── serving

MLOps
├── monitoring
├── drift detection
├── retraining
├── CI/CD
└── observability

AI Engineering
├── agent orchestration
├── tool calling
├── approvals
├── audit trails
├── idempotent execution
└── controlled Kubernetes actions
```

The intended outcome is a production-style ML/AI engineering platform where model operations are observable, reviewable and controlled rather than hidden behind an autonomous black box.

---

## License

Add a project license before publishing the repository as a reusable open-source package.