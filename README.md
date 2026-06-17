# Credit Scoring MLOps

Production-style machine learning project for credit default prediction.

## Goal

The goal of this project is to build a credit scoring system that predicts the probability of loan default.

## Stack

- Python
- Pandas
- Scikit-learn
- CatBoost
- LightGBM
- XGBoost
- MLflow
- DVC
- Great Expectations
- FastAPI
- Docker
- Kafka
- Feast
- Airflow
- PySpark
- Evidently

## Project Stages

### v1: Offline Training
- Load raw data
- Validate data with Great Expectations
- Build features
- Train CatBoost, LightGBM, XGBoost
- Track experiments with MLflow
- Register best model

### v2: Realtime API
- FastAPI service
- Model loading from MLflow Registry
- Docker

### v3: Event-driven scoring
- Kafka producer
- Kafka consumer
- PostgreSQL logging

### v4: Feature Store
- Feast
- Redis online store
- Offline store

### v5: Batch pipelines
- Airflow
- PySpark

### v6: Monitoring
- Evidently
- Data drift
- Prediction drift
- Retraining signal