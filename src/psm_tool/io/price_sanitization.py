from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd


def is_valid_price(value: object) -> bool:
    if value is None:
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric) and numeric >= 0.0


def filter_valid_prices(values: Iterable[object]) -> list[float]:
    return [float(value) for value in values if is_valid_price(value)]


def sanitize_negative_price_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, dict[str, int]]:
    out = df.copy()
    counts: dict[str, int] = {}
    for column in columns:
        if column not in out.columns:
            continue
        numeric = pd.to_numeric(out[column], errors="coerce")
        negative_mask = numeric < 0.0
        counts[column] = int(negative_mask.fillna(False).sum())
        out[column] = numeric.mask(negative_mask)
    return out, counts
