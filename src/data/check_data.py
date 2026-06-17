from pathlib import Path
import pandas as pd


RAW_DATA_PATH = Path("data/raw/german_credit_data.csv")


def main() -> None:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {RAW_DATA_PATH}")

    df = pd.read_csv(RAW_DATA_PATH)

    print("Dataset loaded successfully")
    print(f"Shape: {df.shape}")
    print("\nColumns:")
    print(df.columns.tolist())
    print("\nFirst rows:")
    print(df.head())
    print("\nMissing values:")
    print(df.isnull().sum())


if __name__ == "__main__":
    main()