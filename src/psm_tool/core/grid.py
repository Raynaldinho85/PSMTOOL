from __future__ import annotations

import math

import numpy as np
import pandas as pd

from psm_tool.config import GridConfig

PRICE_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]


def _nice_step(raw_step: float) -> float:
    if raw_step <= 0:
        return 1.0
    exponent = math.floor(math.log10(raw_step))
    fraction = raw_step / (10**exponent)
    if fraction <= 1:
        nice_fraction = 1
    elif fraction <= 2:
        nice_fraction = 2
    elif fraction <= 5:
        nice_fraction = 5
    else:
        nice_fraction = 10
    return float(nice_fraction * (10**exponent))


def _snap_value(value: float, increment: float, mode: str) -> float:
    base = value / increment
    if mode == "floor":
        return math.floor(base) * increment
    return math.ceil(base) * increment


def _round_up_multiple(value: float, increment: float) -> float:
    return math.ceil(value / increment) * increment


def _currency_increment(grid_config: GridConfig, currency: str | None) -> float | None:
    if not grid_config.snap_enabled or not currency:
        return None
    return grid_config.currency_snap.get(str(currency).upper())


def build_price_grid(
    df_group: pd.DataFrame,
    grid_config: GridConfig | None = None,
    currency: str | None = None,
) -> np.ndarray:
    cfg = grid_config or GridConfig()
    prices = df_group[PRICE_COLUMNS].to_numpy(dtype=float).ravel()
    prices = prices[~np.isnan(prices)]
    if len(prices) == 0:
        raise ValueError("Cannot build grid: no numeric threshold values available.")

    raw_min = float(np.floor(np.min(prices)))
    raw_max = float(np.ceil(np.max(prices)))
    data_range = max(raw_max - raw_min, 1.0)
    derived_step = _nice_step(data_range / 120.0)

    increment = _currency_increment(cfg, currency)

    if cfg.mode == "manual":
        if cfg.min_price is None or cfg.max_price is None or cfg.step is None:
            raise ValueError("Manual grid mode requires min_price, max_price, and step.")
        min_price = float(cfg.min_price)
        max_price = float(cfg.max_price)
        step = float(cfg.step)
    else:
        min_price = raw_min
        max_price = raw_max
        step = derived_step

    if increment is not None:
        min_price = _snap_value(min_price, increment, mode="floor")
        max_price = _snap_value(max_price, increment, mode="ceil")
        step = max(step, increment)
        step = _round_up_multiple(step, increment)

    if step <= 0:
        raise ValueError("Grid step must be > 0.")
    if max_price < min_price:
        raise ValueError("Grid max_price must be >= min_price.")

    span = max_price - min_price
    count = int(math.floor(span / step)) + 1
    grid = min_price + np.arange(count, dtype=float) * step
    if len(grid) == 0 or not np.isclose(grid[-1], max_price):
        grid = np.append(grid, max_price)

    return np.unique(np.round(grid, 10))
