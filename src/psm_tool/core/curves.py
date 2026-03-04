from __future__ import annotations

import numpy as np
import pandas as pd

METRIC_DEFINITIONS: dict[str, tuple[str, str]] = {
    "too_cheap": ("too_cheap", ">="),
    "bargain": ("bargain", ">="),
    "expensive": ("expensive_acceptable", "<="),
    "too_expensive": ("too_expensive", "<="),
}


def resolve_psm_weights(df: pd.DataFrame, weight_col: str | None) -> tuple[np.ndarray, bool]:
    if weight_col and weight_col in df.columns:
        weights = pd.to_numeric(df[weight_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        weights[weights < 0] = 0.0
        if float(np.sum(weights)) > 0.0:
            return weights, True
        return np.ones(len(df), dtype=float), False
    return np.ones(len(df), dtype=float), False


def _metric_curve(
    values: np.ndarray, weights: np.ndarray, prices: np.ndarray, op: str
) -> np.ndarray:
    if len(values) == 0:
        return np.full_like(prices, np.nan, dtype=float)

    output = np.empty(len(prices), dtype=float)
    total = float(np.sum(weights))
    if total <= 0:
        return np.full_like(prices, np.nan, dtype=float)

    for idx, price in enumerate(prices):
        if op == ">=":
            mask = values >= price
        else:
            mask = values <= price
        output[idx] = float(np.sum(weights[mask]) / total * 100.0)
    return output


def compute_psm_curves(
    df_group: pd.DataFrame,
    prices: np.ndarray,
    weight_col: str | None = None,
) -> pd.DataFrame:
    prices = np.asarray(prices, dtype=float)
    result = pd.DataFrame({"price": prices})
    weights_all, _weighted = resolve_psm_weights(df_group, weight_col)

    for output_name, (source_col, op) in METRIC_DEFINITIONS.items():
        source = pd.to_numeric(df_group[source_col], errors="coerce").to_numpy(dtype=float)
        valid = ~np.isnan(source)
        values = source[valid]
        weights = weights_all[valid]
        result[output_name] = _metric_curve(values, weights, prices, op)

    result["not_bargain"] = 100.0 - result["bargain"]
    result["not_expensive"] = 100.0 - result["expensive"]
    return result
