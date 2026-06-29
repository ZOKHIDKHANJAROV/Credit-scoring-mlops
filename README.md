# Credit Scoring MLOps

Production-style MLOps project for credit default prediction.

The project demonstrates an end-to-end machine learning system:

- data validation
- feature engineering
- model training
- experiment tracking
- model registry
- model promotion
- FastAPI inference service
- PostgreSQL scoring logs
- Evidently data drift monitoring
- Docker Compose infrastructure
- DVC pipeline
- GitHub Actions CI

## Tech Stack

- Python
- Pandas
- Scikit-learn
- CatBoost
- LightGBM
- XGBoost
- MLflow
- DVC
- PostgreSQL
- MinIO
- FastAPI
- Docker Compose
- Evidently
- Pytest
- GitHub Actions

## Architecture

```text
Raw Data
  ↓
Data Validation
  ↓
Feature Engineering
  ↓
Model Training: CatBoost / LightGBM / XGBoost
  ↓
MLflow Tracking + Model Registry
  ↓
Champion Model Promotion
  ↓
FastAPI Inference Service
  ↓
PostgreSQL Scoring Logs
  ↓
Evidently Drift Monitoring

## Model Results

Best model: CatBoost

Model	ROC-AUC	Gini	Accuracy	F1
CatBoost	0.7642	0.5283	0.6950	0.5271
LightGBM	0.7602	0.5205	0.7550	0.5812
XGBoost	0.7588	0.5176	0.7200	0.5172

Champion model:

CreditScoringCatBoost@champion
Run Infrastructure
docker compose up -d --build

Services:

Service	URL
FastAPI	http://127.0.0.1:8000/docs
MLflow	http://127.0.0.1:5000
MinIO Console	http://127.0.0.1:9001
PostgreSQL	127.0.0.1:55432
Run Training Pipeline
dvc repro
Run API Locally
uvicorn services.api.main:app --port 8000
Example API Response
{
  "default_probability": 0.4435,
  "score": 607,
  "risk_level": "medium",
  "decision": "manual_review",
  "model_name": "CreditScoringCatBoost"
}
Scoring Logs

The API stores prediction results in PostgreSQL table:

scoring_logs

Example check:

docker exec -it credit_scoring_postgres psql -U mlflow -d mlflow
SELECT id, age, credit_amount, default_probability, score, risk_level, decision, created_at
FROM scoring_logs
ORDER BY created_at DESC
LIMIT 5;
Data Drift Monitoring

Generate Evidently drift report:

python -m src.monitoring.drift_report

Outputs:

reports/data_drift_report.html
reports/retrain_signal.json
Tests

Run tests locally:

pytest -v

Current result:

11 passed
CI

GitHub Actions automatically runs tests on every push and pull request.

Workflow file:

.github/workflows/ci.yml
Project Status

## Model Explainability

The project includes SHAP-based explainability for the champion model.
SHAP summary report shows which features have the strongest impact on credit default prediction.

Completed:

DVC pipeline
MLflow tracking
MLflow model registry
champion model alias
FastAPI inference
Docker Compose infrastructure
PostgreSQL scoring logs
Evidently monitoring
retrain signal
pytest tests
SHAP explainability
GitHub Actions CI

Next possible improvements:

Airflow batch pipeline
Kafka real-time scoring
Feast feature store
model explainability with SHAP
dashboard for monitoring

Run:
git clone
python -m venv .venv
pip install -r requirements.txt
docker compose up -d --build
python scripts/restore_german_credit_data.py
dvc repro -f