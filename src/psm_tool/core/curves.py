from __future__ import annotations

import numpy as np
import pandas as pd

METRIC_DEFINITIONS = {
    "too_cheap": ("too_cheap", ">="),
    "bargain": ("bargain", ">="),
    "expensive": ("expensive_acceptable", "<="),
    "too_expensive": ("too_expensive", "<="),
}


def _metric_share(values: np.ndarray, weights: np.ndarray, price: float, op: str) -> float:
    if op == ">=":
        mask = values >= price
    else:
        mask = values <= price

    if mask.size == 0:
        return float("nan")
    total = weights.sum()
    if total <= 0:
        return float("nan")
    return float(weights[mask].sum() / total * 100.0)


def compute_psm_curves(
    df_group: pd.DataFrame, prices: np.ndarray, weight_col: str | None = None
) -> pd.DataFrame:
    result = pd.DataFrame({"price": prices})
    if weight_col and weight_col in df_group.columns:
        base_weights = (
            pd.to_numeric(df_group[weight_col], errors="coerce").fillna(0).to_numpy(dtype=float)
        )
    else:
        base_weights = np.ones(len(df_group), dtype=float)

    for metric_name, (column, op) in METRIC_DEFINITIONS.items():
        values = pd.to_numeric(df_group[column], errors="coerce").to_numpy(dtype=float)
        valid = ~np.isnan(values)
        metric_values = values[valid]
        metric_weights = base_weights[valid]
        curve = [
            _metric_share(metric_values, metric_weights, price=float(price), op=op)
            for price in prices
        ]
        result[metric_name] = curve

    result["not_bargain"] = 100.0 - result["bargain"]
    result["not_expensive"] = 100.0 - result["expensive"]
    return result
