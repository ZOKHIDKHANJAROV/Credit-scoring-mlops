from pathlib import Path

import pandas as pd


URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data"

COLUMNS = [
    "laufkont", "laufzeit", "moral", "verw", "hoehe", "sparkont",
    "beszeit", "rate", "famges", "buerge", "wohnzeit", "verm",
    "alter", "weitkred", "wohn", "bishkred", "beruf", "pers",
    "telef", "gastarb", "kredit",
]

OUTPUT_PATH = Path("data/raw/german_credit_data.csv")


def code_to_int(value: str) -> int:
    """
    Converts UCI categorical codes like A11, A34, A173 to numeric category codes:
    A11 -> 1
    A34 -> 4
    A173 -> 3
    """
    if isinstance(value, str) and value.startswith("A"):
        return int(value[-1])
    return value


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(URL, sep=" ", header=None, names=COLUMNS)

    for column in df.columns:
        if df[column].dtype == "object":
            df[column] = df[column].apply(code_to_int)

    # UCI target: 1 = good, 2 = bad
    # Our old project expected: 0 = good, 1 = bad before feature script flips it.
    # So here we convert:
    # 1 -> 1
    # 2 -> 0
    # Then build_features.py does: target = 1 - original_target
    # Final target becomes:
    # 0 = good
    # 1 = bad
    df["kredit"] = df["kredit"].map({1: 1, 2: 0})

    df.to_csv(OUTPUT_PATH, index=False)

    print("German credit dataset restored")
    print(f"Path: {OUTPUT_PATH}")
    print(f"Shape: {df.shape}")
    print("Columns:")
    print(list(df.columns))
    print("Target distribution:")
    print(df["kredit"].value_counts(normalize=True).sort_index())


if __name__ == "__main__":
    main()