from typing import Any

import pandas as pd
import shap


def get_top_reasons(model: Any, features: pd.DataFrame, top_n: int = 3) -> list[dict]:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)

    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    row_values = shap_values[0]

    reasons = []

    for feature_name, feature_value, shap_value in zip(
        features.columns,
        features.iloc[0].values,
        row_values,
    ):
        if shap_value > 0:
            impact = "increased_risk"
        else:
            impact = "decreased_risk"

        reasons.append(
            {
                "feature": feature_name,
                "value": float(feature_value),
                "shap_value": round(float(shap_value), 4),
                "impact": impact,
            }
        )

    reasons = sorted(
        reasons,
        key=lambda item: abs(item["shap_value"]),
        reverse=True,
    )

    return reasons[:top_n]