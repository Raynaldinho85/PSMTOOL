from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from psm_tool.config import GridConfig

PRICE_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]
TARGET_POINTS = 100
MIN_QUANTILE_VALUES = 20


@dataclass(slots=True)
class PriceGridResult:
    prices: np.ndarray
    min_price: float
    max_price: float
    step: float
    increment: float | None
    snapped: bool
    p05: float | None = None
    p95: float | None = None
    method: str = "legacy"


def _nice_step(raw_step: float) -> float:
    if raw_step <= 0:
        return 1.0
    exponent = math.floor(math.log10(raw_step))
    fraction = raw_step / (10**exponent)
    if fraction <= 1.0:
        base = 1.0
    elif fraction <= 2.0:
        base = 2.0
    elif fraction <= 5.0:
        base = 5.0
    else:
        base = 10.0
    return base * (10**exponent)


def _resolution_step(values: np.ndarray) -> float:
    unique_values = np.unique(np.sort(values))
    if len(unique_values) < 2:
        return 1.0
    diffs = np.diff(unique_values)
    positive = diffs[diffs > 0]
    if len(positive) == 0:
        return 1.0
    return float(np.min(positive))


def _snap_value(value: float, increment: float, mode: str) -> float:
    base = value / increment
    if mode == "floor":
        return math.floor(base) * increment
    return math.ceil(base) * increment


def _round_up_multiple(value: float, increment: float) -> float:
    return math.ceil(value / increment) * increment


def _get_increment(cfg: GridConfig, currency: str | None) -> float | None:
    if not cfg.snap_enabled or not currency:
        return None
    return cfg.currency_snap.get(str(currency).upper())


def _psm_valid_threshold_values(df_group: pd.DataFrame) -> np.ndarray:
    numeric = df_group[PRICE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    complete = numeric.notna().all(axis=1)
    ordered = (
        (numeric["too_cheap"] < numeric["bargain"])
        & (numeric["bargain"] < numeric["expensive_acceptable"])
        & (numeric["expensive_acceptable"] < numeric["too_expensive"])
    )
    valid = complete & ordered
    valid_values = numeric.loc[valid].to_numpy(dtype=float).ravel()
    return valid_values[~np.isnan(valid_values)]


def _legacy_auto_bounds_step(values: np.ndarray) -> tuple[float, float, float]:
    raw_min = float(np.floor(np.min(values)))
    raw_max = float(np.ceil(np.max(values)))
    data_range = max(raw_max - raw_min, 1.0)
    derived_step = max(_nice_step(data_range / 120.0), _resolution_step(values))
    return raw_min, raw_max, float(derived_step)


def build_price_grid_details(
    df_group: pd.DataFrame,
    grid_config: GridConfig | None = None,
    currency: str | None = None,
) -> PriceGridResult:
    cfg = grid_config or GridConfig()
    values = _psm_valid_threshold_values(df_group)
    if len(values) == 0:
        raise ValueError("Cannot build grid: no numeric threshold values available.")

    legacy_min, legacy_max, legacy_step = _legacy_auto_bounds_step(values)
    p05: float | None = None
    p95: float | None = None
    method = "legacy"

    if cfg.mode == "manual":
        if cfg.min_price is None or cfg.max_price is None or cfg.step is None:
            raise ValueError("Manual mode requires min_price, max_price, and step.")
        min_price = float(cfg.min_price)
        max_price = float(cfg.max_price)
        step = float(cfg.step)
    else:
        if len(values) >= MIN_QUANTILE_VALUES:
            p05_candidate = float(np.quantile(values, 0.05))
            p95_candidate = float(np.quantile(values, 0.95))
            if (
                np.isfinite(p05_candidate)
                and np.isfinite(p95_candidate)
                and p95_candidate > p05_candidate
            ):
                span = p95_candidate - p05_candidate
                min_price = max(0.0, p05_candidate - 0.25 * span)
                max_price = p95_candidate + 0.25 * span
                step = float("nan")
                p05 = p05_candidate
                p95 = p95_candidate
                method = "quantile"
            else:
                min_price = legacy_min
                max_price = legacy_max
                step = legacy_step
        else:
            min_price = legacy_min
            max_price = legacy_max
            step = legacy_step

    increment = _get_increment(cfg, currency)
    snapped = increment is not None
    if increment is not None:
        min_price = _snap_value(min_price, increment, mode="floor")
        max_price = _snap_value(max_price, increment, mode="ceil")
        if method != "quantile":
            step = max(step, increment)
            step = _round_up_multiple(step, increment)

    if cfg.mode == "auto" and method == "quantile":
        step_raw = max((max_price - min_price) / TARGET_POINTS, 1e-12)
        step = _nice_step(step_raw)
        if increment is not None:
            step = max(step, increment)
            step = _round_up_multiple(step, increment)

    if step <= 0:
        raise ValueError("Grid step must be > 0.")
    if max_price < min_price:
        raise ValueError("Grid max_price must be >= min_price.")

    prices = np.arange(min_price, max_price + step, step, dtype=float)
    prices = prices[prices <= (max_price + 1e-12)]
    if len(prices) == 0 or not np.isclose(prices[-1], max_price):
        prices = np.append(prices, max_price)

    prices = np.unique(np.round(prices, 10))
    return PriceGridResult(
        prices=prices,
        min_price=float(prices[0]),
        max_price=float(prices[-1]),
        step=float(step),
        increment=increment,
        snapped=snapped,
        p05=p05,
        p95=p95,
        method=method,
    )


def build_price_grid(
    df_group: pd.DataFrame,
    grid_config: GridConfig | None = None,
    currency: str | None = None,
) -> np.ndarray:
    return build_price_grid_details(df_group, grid_config=grid_config, currency=currency).prices
