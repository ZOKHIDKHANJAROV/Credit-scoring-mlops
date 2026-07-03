# Credit Scoring MLOps

Production-style end-to-end MLOps project for credit default prediction.

This project demonstrates how a machine learning model can be trained, registered, deployed, monitored, explained, and used in both API-based and Kafka-based real-time scoring workflows.

---

## Project Overview

The goal of this project is to predict credit default risk using classical machine learning models and build a production-style MLOps system around the model.

The project includes:

- Data validation
- Feature engineering
- DVC pipeline
- Model training with CatBoost, LightGBM and XGBoost
- MLflow experiment tracking
- MLflow Model Registry
- Champion model promotion
- FastAPI inference service
- PostgreSQL scoring logs
- SHAP explainability
- Evidently data drift monitoring
- Retrain signal generation
- Prometheus metrics
- Grafana dashboard
- Airflow batch and retraining pipelines
- Kafka / Redpanda real-time scoring
- Pytest unit tests
- GitHub Actions CI
- Docker Compose infrastructure

---

## Architecture

```text
                    ┌──────────────────────┐
                    │      Raw Data         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Data Validation     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Feature Engineering   │
                    └──────────┬───────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────┐
        │  Model Training                           │
        │  CatBoost / LightGBM / XGBoost            │
        └──────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │ MLflow Tracking + Model Registry          │
        └──────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │ Champion Model Promotion                  │
        │ CreditScoringCatBoost@champion            │
        └──────────┬───────────────────────────────┘
                   │
       ┌───────────┴────────────────────────────┐
       │                                        │
       ▼                                        ▼
┌──────────────────────┐              ┌──────────────────────┐
│ FastAPI Scoring API   │              │ Kafka Consumer        │
│ /score                │              │ Real-time scoring     │
└──────────┬───────────┘              └──────────┬───────────┘
           │                                     │
           ▼                                     ▼
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL scoring_logs                                      │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ Prometheus + Grafana Monitoring                              │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ Airflow Batch Monitoring + Retraining Pipelines              │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Area | Tools |
|---|---|
| Language | Python |
| Data Processing | Pandas, NumPy |
| ML Models | CatBoost, LightGBM, XGBoost |
| Experiment Tracking | MLflow |
| Model Registry | MLflow Model Registry |
| Pipeline Versioning | DVC |
| API | FastAPI |
| Database | PostgreSQL |
| Object Storage | MinIO |
| Monitoring | Prometheus, Grafana |
| Drift Detection | Evidently |
| Explainability | SHAP |
| Orchestration | Apache Airflow |
| Streaming | Redpanda / Kafka |
| Testing | Pytest |
| CI | GitHub Actions |
| Infrastructure | Docker Compose |

---

## Main Features

### Machine Learning

- Credit default prediction
- CatBoost, LightGBM and XGBoost training
- Model comparison by ROC-AUC
- Champion model selection
- MLflow experiment tracking
- MLflow Model Registry
- Champion model alias

### API Serving

- FastAPI inference endpoint
- Credit score calculation
- Risk level classification
- Decision logic:
  - `approved`
  - `manual_review`
  - `rejected`
- PostgreSQL scoring logs
- SHAP local explanations for each prediction

### Kafka Real-time Scoring

- Kafka-compatible Redpanda broker
- `credit_applications` topic
- `scoring_results` topic
- Producer script for generating credit applications
- Dockerized Kafka consumer
- Real-time scoring using MLflow champion model
- Results written to PostgreSQL and Kafka

### Monitoring

- Prometheus metrics
- Grafana dashboard
- API request metrics
- Error metrics
- Latency metrics
- Decision distribution
- Risk level distribution
- Retrain required signal

### Airflow

- Batch monitoring DAG
- Full retraining DAG
- Data validation
- Feature engineering
- Drift report generation
- SHAP report generation
- Model retraining pipeline

---

## Project Structure

```text
Credit-scoring-mlops/
│
├── configs/
│   └── feature_config.json
│
├── dags/
│   ├── credit_scoring_batch_pipeline.py
│   └── credit_scoring_retraining_pipeline.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       ├── provisioning/
│       └── dashboards/
│
├── reports/
│   ├── data_drift_report.html
│   ├── retrain_signal.json
│   ├── shap_summary.html
│   └── shap_summary.png
│
├── scripts/
│   ├── restore_german_credit_data.py
│   ├── generate_scoring_logs.py
│   ├── kafka_producer.py
│   └── kafka_consume_results.py
│
├── services/
│   ├── api/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── scoring.py
│   │   ├── explainability.py
│   │   ├── metrics.py
│   │   ├── model_loader.py
│   │   └── db/
│   │       ├── database.py
│   │       ├── models.py
│   │       └── repository.py
│   │
│   └── kafka_consumer/
│       └── scoring_consumer.py
│
├── src/
│   ├── data/
│   │   ├── schema.py
│   │   └── validate_data.py
│   │
│   ├── features/
│   │   └── build_features.py
│   │
│   ├── training/
│   │   ├── train_catboost.py
│   │   ├── train_lightgbm.py
│   │   ├── train_xgboost.py
│   │   ├── select_best_model.py
│   │   └── promote_model.py
│   │
│   ├── monitoring/
│   │   └── drift_report.py
│   │
│   └── explainability/
│       └── shap_report.py
│
├── tests/
│   └── test_scoring.py
│
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.kafka
├── requirements.txt
├── requirements-airflow.txt
├── requirements-kafka.txt
├── dvc.yaml
├── dvc.lock
├── pytest.ini
└── README.md
```

---

## Model Results

Best model: **CatBoost**

| Model | ROC-AUC | Gini | Accuracy | F1 |
|---|---:|---:|---:|---:|
| CatBoost | 0.8139 | 0.6279 | 0.7400 | 0.6232 |
| LightGBM | 0.7669 | 0.5338 | 0.7150 | 0.5649 |
| XGBoost | 0.8038 | 0.6076 | 0.7650 | 0.6179 |

Champion model:

```text
CreditScoringCatBoost@champion
```

---

## Services

After running Docker Compose, the following services are available:

| Service | URL |
|---|---|
| FastAPI Swagger | http://127.0.0.1:8000/docs |
| FastAPI Metrics | http://127.0.0.1:8000/metrics |
| MLflow UI | http://127.0.0.1:5000 |
| MinIO Console | http://127.0.0.1:9001 |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 |
| Airflow | http://127.0.0.1:8080 |
| Kafka UI | http://127.0.0.1:8081 |
| PostgreSQL | 127.0.0.1:55432 |

Default credentials:

| Service | Username | Password |
|---|---|---|
| Grafana | admin | admin |
| Airflow | admin | admin |
| MinIO | minio | minio123 |

---

## Quick Start

### 1. Clone repository

```bash
git clone https://github.com/ZOKHIDKHANJAROV/Credit-scoring-mlops.git
cd Credit-scoring-mlops
```

### 2. Create virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start infrastructure

```bash
docker compose up -d --build
```

### 5. Restore dataset

```bash
python -m scripts.restore_german_credit_data
```

### 6. Run DVC pipeline

```bash
dvc repro
```

---

## DVC Pipeline

The project uses DVC to reproduce the full ML workflow.

Main stages:

```text
validate_data
build_features
train_catboost
train_lightgbm
train_xgboost
select_best_model
promote_model
drift_report
shap_report
```

Run full pipeline:

```bash
dvc repro
```

Run a specific stage:

```bash
dvc repro train_catboost
```

---

## FastAPI Scoring API

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Endpoint:

```text
POST /score
```

Example response:

```json
{
  "default_probability": 0.6456,
  "score": 495,
  "risk_level": "high",
  "decision": "rejected",
  "model_name": "CreditScoringCatBoost",
  "top_reasons": [
    {
      "feature": "duration_months",
      "value": 1,
      "shap_value": -0.6403,
      "impact": "decreased_risk"
    },
    {
      "feature": "checking_account_status",
      "value": 1,
      "shap_value": 0.5301,
      "impact": "increased_risk"
    },
    {
      "feature": "other_installment_plans",
      "value": 1,
      "shap_value": 0.4834,
      "impact": "increased_risk"
    }
  ]
}
```

The API returns:

| Field | Meaning |
|---|---|
| `default_probability` | Probability of default |
| `score` | Credit score from 300 to 850 |
| `risk_level` | low / medium / high / very_high |
| `decision` | approved / manual_review / rejected |
| `top_reasons` | SHAP-based local explanation |

---

## Scoring Logs

Every API and Kafka prediction is saved into PostgreSQL table:

```text
scoring_logs
```

Check latest scoring logs through API:

```text
http://127.0.0.1:8000/scoring-logs
```

Or through PostgreSQL:

```bash
docker exec -it credit_scoring_postgres psql -U mlflow -d mlflow
```

```sql
SELECT id, age, credit_amount, default_probability, score, risk_level, decision, created_at
FROM scoring_logs
ORDER BY created_at DESC
LIMIT 5;
```

---

## Kafka Real-time Scoring

This project includes Kafka-compatible real-time scoring using Redpanda.

Topics:

```text
credit_applications
scoring_results
```

Flow:

```text
kafka_producer.py
      ↓
credit_applications topic
      ↓
kafka-consumer Docker service
      ↓
MLflow champion model
      ↓
PostgreSQL scoring_logs
      ↓
scoring_results topic
```

### Start Kafka services

```bash
docker compose up -d redpanda kafka-ui kafka-consumer
```

### Create topics

```bash
docker exec -it credit_scoring_redpanda rpk topic create credit_applications
docker exec -it credit_scoring_redpanda rpk topic create scoring_results
```

List topics:

```bash
docker exec -it credit_scoring_redpanda rpk topic list
```

### Send applications to Kafka

```bash
python -m scripts.kafka_producer
```

### Read scoring results from terminal

```bash
python -m scripts.kafka_consume_results
```

### Kafka UI

```text
http://127.0.0.1:8081
```

Check:

```text
Topics → scoring_results → Messages
```

---

## Airflow Pipelines

Airflow UI:

```text
http://127.0.0.1:8080
```

Login:

```text
admin / admin
```

### Batch Monitoring DAG

```text
credit_scoring_batch_pipeline
```

Pipeline:

```text
validate_data
    ↓
build_features
    ↓
drift_report
    ↓
shap_report
```

This DAG generates:

```text
reports/data_drift_report.html
reports/retrain_signal.json
reports/shap_summary.html
reports/shap_summary.png
```

### Retraining DAG

```text
credit_scoring_retraining_pipeline
```

Pipeline:

```text
validate_data
    ↓
build_features
    ↓
train_catboost / train_lightgbm / train_xgboost
    ↓
select_best_model
    ↓
promote_model
    ↓
shap_report
```

This DAG runs full model retraining and promotes the best model to MLflow Registry.

---

## Data Drift Monitoring

Generate Evidently drift report manually:

```bash
python -m src.monitoring.drift_report
```

Outputs:

```text
reports/data_drift_report.html
reports/retrain_signal.json
```

Example retrain signal:

```json
{
  "retrain_required": false,
  "reason": "No data drift detected",
  "drifted_features": []
}
```

---

## Prometheus Metrics

FastAPI exposes metrics at:

```text
http://127.0.0.1:8000/metrics
```

Important metrics:

```text
credit_scoring_requests_total
credit_scoring_errors_total
credit_scoring_default_probability
credit_scoring_score
credit_scoring_decision_total
credit_scoring_risk_level_total
credit_scoring_request_latency_seconds
credit_scoring_retrain_required
```

Prometheus UI:

```text
http://127.0.0.1:9090
```

Example query:

```text
credit_scoring_retrain_required
```

---

## Grafana Dashboard

Grafana UI:

```text
http://127.0.0.1:3000
```

Login:

```text
admin / admin
```

Dashboard:

```text
Credit Scoring Monitoring
```

Panels:

- Total Scoring Requests
- Scoring Errors
- Last Default Probability
- Last Credit Score
- Requests Per Minute
- API Latency
- Decision Distribution
- Risk Level Distribution
- Retrain Required

Retrain panel:

```text
No  → credit_scoring_retrain_required = 0
Yes → credit_scoring_retrain_required = 1
```

---

## SHAP Explainability

The project includes two types of explainability.

### 1. Global SHAP Report

Generated by:

```bash
python -m src.explainability.shap_report
```

Outputs:

```text
reports/shap_summary.html
reports/shap_summary.png
```

This report shows which features have the strongest global impact on credit default prediction.

### 2. Local SHAP Explanations in API

The `/score` endpoint returns `top_reasons`, which explain why a specific application received its score and decision.

Example:

```json
"top_reasons": [
  {
    "feature": "checking_account_status",
    "value": 1,
    "shap_value": 0.5301,
    "impact": "increased_risk"
  }
]
```

---

## Testing

Run tests:

```bash
pytest -v
```

Current tests cover:

- Score conversion
- Risk level logic
- Decision logic
- Feature generation
- API scoring helper functions

Current result:

```text
11 passed
```

---

## CI/CD

GitHub Actions runs tests on every push and pull request.

Workflow file:

```text
.github/workflows/ci.yml
```

---

## Docker Compose Services

Main containers:

```text
credit_scoring_postgres
credit_scoring_minio
credit_scoring_mlflow
credit_scoring_api
credit_scoring_prometheus
credit_scoring_grafana
credit_scoring_airflow_webserver
credit_scoring_airflow_scheduler
credit_scoring_redpanda
credit_scoring_kafka_ui
credit_scoring_kafka_consumer
```

Start all services:

```bash
docker compose up -d --build
```

Stop all services:

```bash
docker compose down
```

View logs:

```bash
docker logs credit_scoring_api --tail 100
docker logs credit_scoring_kafka_consumer --tail 100
docker logs credit_scoring_airflow_webserver --tail 100
```

---

## Environment Notes

Local Python scripts use:

```text
MLflow: http://127.0.0.1:5000
MinIO: http://127.0.0.1:9000
PostgreSQL: 127.0.0.1:55432
Kafka: 127.0.0.1:19092
```

Docker services use internal Docker hostnames:

```text
MLflow: http://mlflow:5000
MinIO: http://minio:9000
PostgreSQL: postgres:5432
Kafka: redpanda:9092
```

This difference is important when running scripts locally or inside Docker containers.

---

## How to Run on a New Machine

```bash
git clone https://github.com/ZOKHIDKHANJAROV/Credit-scoring-mlops.git
cd Credit-scoring-mlops
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start infrastructure:

```bash
docker compose up -d --build
```

Restore dataset:

```bash
python -m scripts.restore_german_credit_data
```

Run training pipeline:

```bash
dvc repro
```

Open:

```text
FastAPI:    http://127.0.0.1:8000/docs
MLflow:     http://127.0.0.1:5000
Grafana:    http://127.0.0.1:3000
Airflow:    http://127.0.0.1:8080
Kafka UI:   http://127.0.0.1:8081
```

---

## Resume Bullet

```text
Built an end-to-end Credit Scoring MLOps system with DVC pipelines, MLflow Tracking and Model Registry, FastAPI model serving, PostgreSQL prediction logging, Kafka real-time scoring, Airflow orchestration, Evidently drift monitoring, SHAP explainability, Prometheus/Grafana observability, Docker Compose infrastructure, Pytest tests, and GitHub Actions CI.
```

---

## Project Status

Completed:

- DVC pipeline
- MLflow tracking
- MLflow model registry
- Champion model alias
- FastAPI inference
- PostgreSQL scoring logs
- SHAP global explainability
- SHAP local explanations in API
- Evidently drift monitoring
- Retrain signal
- Prometheus metrics
- Grafana dashboard
- Airflow batch pipeline
- Airflow retraining pipeline
- Kafka real-time scoring
- Kafka UI
- Kafka producer
- Kafka consumer
- Pytest tests
- GitHub Actions CI
- Docker Compose infrastructure

Possible future improvements:

- Feast Feature Store
- Dockerfile for Airflow image
- Docker healthchecks
- Makefile or PowerShell automation scripts
- More API integration tests
- Authentication for API
- Model performance monitoring over time
- Batch scoring pipeline
- Cloud deployment

---

## Author

Project by **Vohid Khanzharov**

GitHub:

```text
https://github.com/ZOKHIDKHANJAROV
```