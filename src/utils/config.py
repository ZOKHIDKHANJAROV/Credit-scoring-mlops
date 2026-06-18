import json
from pathlib import Path
from typing import Any


FEATURE_CONFIG_PATH = Path("configs/feature_config.json")


def load_feature_config() -> dict[str, Any]:
    if not FEATURE_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {FEATURE_CONFIG_PATH}")

    with open(FEATURE_CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)