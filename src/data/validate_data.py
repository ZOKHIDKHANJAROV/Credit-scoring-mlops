from pathlib import Path

import pandas as pd

from src.data.schema import EXPECTED_COLUMNS, TARGET_COLUMN


RAW_DATA_PATH = Path("data/raw/german_credit_data.csv")


def validate_columns(df: pd.DataFrame) -> None:
    actual_columns = list(df.columns)

    missing_columns = set(EXPECTED_COLUMNS) - set(actual_columns)
    extra_columns = set(actual_columns) - set(EXPECTED_COLUMNS)

    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    if extra_columns:
        raise ValueError(f"Extra columns: {extra_columns}")

    print("Column validation passed")


def validate_not_null(df: pd.DataFrame) -> None:
    null_counts = df.isnull().sum()
    columns_with_nulls = null_counts[null_counts > 0]

    if not columns_with_nulls.empty:
        raise ValueError(f"Columns with nulls:\n{columns_with_nulls}")

    print("Null validation passed")


def validate_ranges(df: pd.DataFrame) -> None:
    checks = {
        "laufzeit": (1, 100),
        "hoehe": (1, 1_000_000),
        "alter": (18, 100),
        "rate": (1, 10),
        "wohnzeit": (1, 10),
        "bishkred": (1, 10),
    }

    for column, (min_value, max_value) in checks.items():
        invalid_rows = df[
            (df[column] < min_value) | (df[column] > max_value)
        ]

        if not invalid_rows.empty:
            raise ValueError(
                f"Column {column} has values outside range "
                f"[{min_value}, {max_value}]. "
                f"Invalid rows: {len(invalid_rows)}"
            )

    print("Range validation passed")


def validate_target(df: pd.DataFrame) -> None:
    allowed_values = {0, 1}
    actual_values = set(df[TARGET_COLUMN].unique())

    unexpected_values = actual_values - allowed_values

    if unexpected_values:
        raise ValueError(
            f"Unexpected target values in {TARGET_COLUMN}: {unexpected_values}"
        )

    print(f"Target validation passed. Values: {sorted(actual_values)}")


def validate_unique_rows(df: pd.DataFrame) -> None:
    duplicated_count = df.duplicated().sum()

    if duplicated_count > 0:
        raise ValueError(f"Found duplicated rows: {duplicated_count}")

    print("Duplicate validation passed")


def main() -> None:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {RAW_DATA_PATH}")

    df = pd.read_csv(RAW_DATA_PATH)

    validate_columns(df)
    validate_not_null(df)
    validate_ranges(df)
    validate_target(df)
    validate_unique_rows(df)

    print("Data validation completed successfully")


if __name__ == "__main__":
    main()