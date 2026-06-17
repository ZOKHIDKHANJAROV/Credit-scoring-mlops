import subprocess
import sys


COMMANDS = [
    ("Validate raw data", "python -m src.data.validate_data"),
    ("Build features", "python -m src.features.build_features"),
    ("Train CatBoost", "python -m src.training.train_catboost"),
    ("Train LightGBM", "python -m src.training.train_lightgbm"),
    ("Train XGBoost", "python -m src.training.train_xgboost"),
    ("Select best model", "python -m src.training.select_best_model"),
]


def run_command(step_name: str, command: str) -> None:
    print("\n" + "=" * 80)
    print(f"STEP: {step_name}")
    print(f"COMMAND: {command}")
    print("=" * 80)

    result = subprocess.run(command, shell=True)

    if result.returncode != 0:
        print(f"\nPipeline failed at step: {step_name}")
        sys.exit(result.returncode)

    print(f"Step completed: {step_name}")


def main() -> None:
    print("Starting offline training pipeline...")

    for step_name, command in COMMANDS:
        run_command(step_name, command)

    print("\nOffline training pipeline completed successfully")


if __name__ == "__main__":
    main()