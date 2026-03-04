from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

OUTLIER_LEVELS: dict[str, tuple[float, float]] = {
    "mild": (0.005, 0.995),
    "medium": (0.01, 0.99),
    "strict": (0.05, 0.95),
}


@dataclass(slots=True)
class OutlierFilterResult:
    filtered_df: pd.DataFrame
    included_mask: pd.Series
    excluded_n: int
    enabled: bool
    level: str
    q_low: float | None
    q_high: float | None
    bounds: pd.DataFrame


def compute_quantile_bounds(
    df: pd.DataFrame, columns: list[str], q_low: float, q_high: float
) -> pd.DataFrame:
    numeric = df[columns].apply(pd.to_numeric, errors="coerce")
    rows = []
    for column in columns:
        rows.append(
            {
                "column": column,
                "lower": float(numeric[column].quantile(q_low, interpolation="lower")),
                "upper": float(numeric[column].quantile(q_high, interpolation="higher")),
            }
        )
    return pd.DataFrame(rows).set_index("column")


def apply_outlier_filter(
    df: pd.DataFrame,
    columns: list[str],
    *,
    level: Literal["mild", "medium", "strict"] = "medium",
    enabled: bool = False,
) -> OutlierFilterResult:
    if not enabled:
        included_mask = pd.Series(True, index=df.index, dtype=bool)
        return OutlierFilterResult(
            filtered_df=df.copy(),
            included_mask=included_mask,
            excluded_n=0,
            enabled=False,
            level=level,
            q_low=None,
            q_high=None,
            bounds=pd.DataFrame(columns=["lower", "upper"]),
        )

    q_low, q_high = OUTLIER_LEVELS[level]
    bounds = compute_quantile_bounds(df, columns, q_low=q_low, q_high=q_high)
    numeric = df[columns].apply(pd.to_numeric, errors="coerce")

    is_outlier = pd.Series(False, index=df.index, dtype=bool)
    for column in columns:
        lower = float(bounds.loc[column, "lower"])
        upper = float(bounds.loc[column, "upper"])
        within = numeric[column].between(lower, upper, inclusive="both")
        # Missing values are not treated as outliers here.
        # PSM validity already handles threshold completeness.
        is_outlier = is_outlier | (~within.fillna(True))

    included_mask = ~is_outlier
    filtered = df.loc[included_mask].copy()
    return OutlierFilterResult(
        filtered_df=filtered,
        included_mask=included_mask,
        excluded_n=int(is_outlier.sum()),
        enabled=True,
        level=level,
        q_low=q_low,
        q_high=q_high,
        bounds=bounds,
    )
