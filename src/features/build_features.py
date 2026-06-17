from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


RAW_DATA_PATH = Path("data/raw/german_credit_data.csv")
PROCESSED_DIR = Path("data/processed")

TRAIN_PATH = PROCESSED_DIR / "train.csv"
TEST_PATH = PROCESSED_DIR / "test.csv"


COLUMN_MAPPING = {
    "laufkont": "checking_account_status",
    "laufzeit": "duration_months",
    "moral": "credit_history",
    "verw": "purpose",
    "hoehe": "credit_amount",
    "sparkont": "savings_account",
    "beszeit": "employment_since",
    "rate": "installment_rate",
    "famges": "personal_status_sex",
    "buerge": "other_debtors",
    "wohnzeit": "residence_since",
    "verm": "property",
    "alter": "age",
    "weitkred": "other_installment_plans",
    "wohn": "housing",
    "bishkred": "existing_credits",
    "beruf": "job",
    "pers": "people_liable",
    "telef": "telephone",
    "gastarb": "foreign_worker",
    "kredit": "original_target",
}


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["credit_amount_per_month"] = (
        df["credit_amount"] / df["duration_months"]
    )

    df["credit_amount_per_age"] = (
        df["credit_amount"] / df["age"]
    )

    df["is_long_term_loan"] = (
        df["duration_months"] >= 36
    ).astype(int)

    df["is_high_amount_loan"] = (
        df["credit_amount"] >= df["credit_amount"].median()
    ).astype(int)

    return df


def main() -> None:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {RAW_DATA_PATH}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAW_DATA_PATH)

    df = df.rename(columns=COLUMN_MAPPING)

    df["target"] = 1 - df["original_target"]
    df = df.drop(columns=["original_target"])
    
    df = add_features(df)

    train_df, test_df = train_test_split(
        df,
        test_size=0.2,
        random_state=42,
        stratify=df["target"],
    )

    train_df.to_csv(TRAIN_PATH, index=False)
    test_df.to_csv(TEST_PATH, index=False)

    print("Feature engineering completed")
    print(f"Train shape: {train_df.shape}")
    print(f"Test shape: {test_df.shape}")
    print(f"Train saved to: {TRAIN_PATH}")
    print(f"Test saved to: {TEST_PATH}")
    print("\nTarget distribution in train:")
    print(train_df["target"].value_counts(normalize=True))


if __name__ == "__main__":
    main()