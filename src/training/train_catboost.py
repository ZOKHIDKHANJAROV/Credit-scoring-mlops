from pathlib import Path

import mlflow
import mlflow.catboost
import pandas as pd
from catboost import CatBoostClassifier
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
    if not TRAIN_PATH.exists():
        raise FileNotFoundError(f"File not found: {TRAIN_PATH}")

    if not TEST_PATH.exists():
        raise FileNotFoundError(f"File not found: {TEST_PATH}")

    train_df = pd.read_csv(TRAIN_PATH)
    test_df = pd.read_csv(TEST_PATH)

    X_train = train_df.drop(columns=[TARGET_COLUMN])
    y_train = train_df[TARGET_COLUMN]

    X_test = test_df.drop(columns=[TARGET_COLUMN])
    y_test = test_df[TARGET_COLUMN]

    return X_train, X_test, y_train, y_test


def get_cat_features(X: pd.DataFrame) -> list[str]:
    categorical_columns = [
        "checking_account_status",
        "credit_history",
        "purpose",
        "savings_account",
        "employment_since",
        "personal_status_sex",
        "other_debtors",
        "property",
        "other_installment_plans",
        "housing",
        "job",
        "people_liable",
        "telephone",
        "foreign_worker",
        "is_long_term_loan",
        "is_high_amount_loan",
    ]

    return [col for col in categorical_columns if col in X.columns]


def calculate_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
    y_proba: pd.Series,
) -> dict[str, float]:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_proba),
        "gini": 2 * roc_auc_score(y_true, y_proba) - 1,
    }


def main() -> None:
    X_train, X_test, y_train, y_test = load_data()

    cat_features = get_cat_features(X_train)

    params = {
        "iterations": 300,
        "learning_rate": 0.05,
        "depth": 4,
        "loss_function": "Logloss",
        "eval_metric": "AUC",
        "random_seed": 42,
        "verbose": False,
        "class_weights": [1.0, 2.0],
    }

    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name="catboost_baseline"):
        model = CatBoostClassifier(**params)

        model.fit(
            X_train,
            y_train,
            cat_features=cat_features,
            eval_set=(X_test, y_test),
            use_best_model=True,
        )

        y_proba = model.predict_proba(X_test)[:, 1]
        y_pred = (y_proba >= 0.5).astype(int)

        metrics = calculate_metrics(y_test, y_pred, y_proba)

        mlflow.log_params(params)
        mlflow.log_param("cat_features", cat_features)
        mlflow.log_metrics(metrics)

        mlflow.catboost.log_model(
            cb_model=model,
            artifact_path="model",
            registered_model_name="CreditScoringCatBoost",
        )

        print("CatBoost training completed")
        print("Metrics:")
        for metric_name, metric_value in metrics.items():
            print(f"{metric_name}: {metric_value:.4f}")


if __name__ == "__main__":
    main()