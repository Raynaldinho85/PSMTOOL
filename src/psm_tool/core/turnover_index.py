from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class TurnoverIndexResult:
    df: pd.DataFrame
    max_turnover_price: float
    max_turnover_index: float


def _as_numeric_array(values: np.ndarray | pd.Series | list[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError("Expected one-dimensional numeric array.")
    if len(array) == 0:
        raise ValueError("Expected at least one value.")
    if not np.all(np.isfinite(array)):
        raise ValueError("Input contains non-finite values.")
    return array


def align_pi_ladder_to_grid(prices: np.ndarray, pi_ladder_df: pd.DataFrame) -> np.ndarray:
    grid = _as_numeric_array(prices)
    if "price" not in pi_ladder_df.columns or "purchase_intention_pct" not in pi_ladder_df.columns:
        raise ValueError("PI ladder must contain 'price' and 'purchase_intention_pct' columns.")

    ladder = pi_ladder_df.copy()
    ladder["price"] = pd.to_numeric(ladder["price"], errors="coerce")
    ladder["purchase_intention_pct"] = pd.to_numeric(
        ladder["purchase_intention_pct"], errors="coerce"
    )
    ladder = ladder.dropna(subset=["price", "purchase_intention_pct"])
    if ladder.empty:
        raise ValueError("PI ladder has no numeric rows after parsing.")

    grouped = (
        ladder.groupby("price", as_index=False)["purchase_intention_pct"]
        .mean()
        .sort_values("price")
        .reset_index(drop=True)
    )
    xp = grouped["price"].to_numpy(dtype=float)
    fp = np.clip(grouped["purchase_intention_pct"].to_numpy(dtype=float), 0.0, 100.0)

    if len(xp) == 1:
        return np.full_like(grid, float(fp[0]), dtype=float)
    return np.interp(grid, xp, fp, left=float(fp[0]), right=float(fp[-1]))


def resolve_purchase_intention_curve(
    prices: np.ndarray,
    *,
    pi_ladder_df: pd.DataFrame | None = None,
    nms_curves: pd.DataFrame | None = None,
) -> tuple[np.ndarray, str]:
    if pi_ladder_df is not None and len(pi_ladder_df) > 0:
        return align_pi_ladder_to_grid(prices, pi_ladder_df), "ladder"

    if nms_curves is not None and {"price", "trial_pct"}.issubset(nms_curves.columns):
        source_prices = _as_numeric_array(nms_curves["price"].to_numpy(dtype=float))
        source_pi = np.clip(
            _as_numeric_array(nms_curves["trial_pct"].to_numpy(dtype=float)), 0.0, 100.0
        )
        grid = _as_numeric_array(prices)
        if len(source_prices) == 1:
            return np.full_like(grid, float(source_pi[0]), dtype=float), "nms_trial"
        return (
            np.interp(
                grid, source_prices, source_pi, left=float(source_pi[0]), right=float(source_pi[-1])
            ),
            "nms_trial",
        )

    raise ValueError("No purchase intention source available (ladder or NMS trial curve required).")


def compute_turnover_index(prices: np.ndarray, pi_pct: np.ndarray) -> TurnoverIndexResult:
    price_arr = _as_numeric_array(prices)
    pi_arr = np.clip(_as_numeric_array(pi_pct), 0.0, 100.0)
    if len(price_arr) != len(pi_arr):
        raise ValueError("prices and pi_pct must have equal length.")

    revenue_raw = price_arr * (pi_arr / 100.0)
    max_revenue = float(np.max(revenue_raw))
    if max_revenue <= 0:
        turnover = np.zeros_like(revenue_raw)
    else:
        turnover = revenue_raw / max_revenue * 100.0

    max_turnover = float(np.max(turnover))
    max_indices = np.flatnonzero(np.isclose(turnover, max_turnover))
    max_index = int(max_indices[0]) if len(max_indices) > 0 else int(np.argmax(turnover))
    max_turnover_price = float(price_arr[max_index])

    frame = pd.DataFrame(
        {
            "price": price_arr,
            "purchase_intention_pct": pi_arr,
            "turnover_index": turnover,
        }
    )
    return TurnoverIndexResult(
        df=frame,
        max_turnover_price=max_turnover_price,
        max_turnover_index=max_turnover,
    )
