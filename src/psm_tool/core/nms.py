from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class NMSResult:
    curves: pd.DataFrame
    max_trial_price: float
    max_revenue_price: float


def _interp_segment(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    if x1 == x0:
        return y1
    ratio = (x - x0) / (x1 - x0)
    return y0 + ratio * (y1 - y0)


def _respondent_trial(row: pd.Series, prices: np.ndarray) -> np.ndarray:
    tc, b, ea, te = [
        float(row[col]) for col in ("too_cheap", "bargain", "expensive_acceptable", "too_expensive")
    ]
    pi_b = float(np.clip(row.get("pi_bargain_pct", 0.0), 0.0, 100.0))
    pi_e = float(np.clip(row.get("pi_expensive_pct", 0.0), 0.0, 100.0))
    output = np.zeros_like(prices, dtype=float)
    for idx, price in enumerate(prices):
        if price <= tc or price >= te:
            output[idx] = 0.0
        elif price <= b:
            output[idx] = _interp_segment(price, tc, 0.0, b, pi_b)
        elif price <= ea:
            output[idx] = _interp_segment(price, b, pi_b, ea, pi_e)
        else:
            output[idx] = _interp_segment(price, ea, pi_e, te, 0.0)
    return output


def compute_nms(
    df_group: pd.DataFrame,
    prices: np.ndarray,
    *,
    weight_col: str | None = None,
) -> NMSResult:
    if len(df_group) == 0:
        empty = pd.DataFrame(
            {
                "price": prices,
                "trial_pct": np.nan,
                "revenue_per_100": np.nan,
                "turnover_index": np.nan,
            }
        )
        return NMSResult(curves=empty, max_trial_price=float("nan"), max_revenue_price=float("nan"))

    if weight_col and weight_col in df_group.columns:
        weights = (
            pd.to_numeric(df_group[weight_col], errors="coerce").fillna(0).to_numpy(dtype=float)
        )
    else:
        weights = np.ones(len(df_group), dtype=float)
    if np.sum(weights) <= 0:
        weights = np.ones(len(df_group), dtype=float)

    respondent_curves = np.vstack(
        [_respondent_trial(row, prices) for _, row in df_group.iterrows()]
    )
    trial_pct = np.average(respondent_curves, axis=0, weights=weights)
    revenue = (trial_pct / 100.0) * prices * 100.0
    max_rev = np.max(revenue) if len(revenue) else 0.0
    turnover = np.zeros_like(revenue)
    if max_rev > 0:
        turnover = revenue / max_rev * 100.0

    max_trial_price = float(prices[int(np.argmax(trial_pct))])
    max_revenue_price = float(prices[int(np.argmax(revenue))])

    curves = pd.DataFrame(
        {
            "price": prices,
            "trial_pct": trial_pct,
            "revenue_per_100": revenue,
            "turnover_index": turnover,
        }
    )
    return NMSResult(
        curves=curves, max_trial_price=max_trial_price, max_revenue_price=max_revenue_price
    )
