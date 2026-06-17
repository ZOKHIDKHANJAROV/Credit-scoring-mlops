from pathlib import Path

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


TRAIN_PATH = Path("data/processed/train.csv")
TEST_PATH = Path("data/processed/test.csv")

TARGET_COLUMN = "target"
EXPERIMENT_NAME = "credit-scoring"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    train_df = pd.read_csv(TRAIN_PATH)
    test_df = pd.read_csv(TEST_PATH)

    X_train = train_df.drop(columns=[TARGET_COLUMN])
    y_train = train_df[TARGET_COLUMN]

    X_test = test_df.drop(columns=[TARGET_COLUMN])
    y_test = test_df[TARGET_COLUMN]

    return X_train, X_test, y_train, y_test


def calculate_metrics(y_true, y_pred, y_proba) -> dict[str, float]:
    roc_auc = roc_auc_score(y_true, y_proba)

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc,
        "gini": 2 * roc_auc - 1,
    }


def main() -> None:
    X_train, X_test, y_train, y_test = load_data()

    params = {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "max_depth": 4,
        "num_leaves": 16,
        "objective": "binary",
        "random_state": 42,
        "class_weight": "balanced",
    }

    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name="lightgbm_baseline"):
        model = lgb.LGBMClassifier(**params)

        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            eval_metric="auc",
        )

        y_proba = model.predict_proba(X_test)[:, 1]
        y_pred = (y_proba >= 0.5).astype(int)

        metrics = calculate_metrics(y_test, y_pred, y_proba)

        mlflow.log_params(params)
        mlflow.log_metrics(metrics)

        mlflow.lightgbm.log_model(
            lgb_model=model,
            artifact_path="model",
            registered_model_name="CreditScoringLightGBM",
        )

        print("LightGBM training completed")
        print("Metrics:")
        for metric_name, metric_value in metrics.items():
            print(f"{metric_name}: {metric_value:.4f}")


if __name__ == "__main__":
    main()