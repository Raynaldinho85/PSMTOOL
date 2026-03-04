from __future__ import annotations

import math

import numpy as np
import pandas as pd

from psm_tool.config import GridConfig
from psm_tool.core.grid import build_price_grid_details


def _nice_number(raw_step: float) -> float:
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


def test_quantile_autogrid_uses_robust_bounds_with_large_sample() -> None:
    rows = []
    for i in range(100):
        rows.append(
            {
                "too_cheap": 100 + i,
                "bargain": 130 + i,
                "expensive_acceptable": 160 + i,
                "too_expensive": 190 + i,
            }
        )
    rows.append(
        {
            "too_cheap": 5000,
            "bargain": 6000,
            "expensive_acceptable": 7000,
            "too_expensive": 8000,
        }
    )
    df = pd.DataFrame(rows)
    details = build_price_grid_details(df, GridConfig(), currency="EUR")

    assert details.method == "quantile"
    assert details.p05 is not None
    assert details.p95 is not None
    assert details.max_price == 500.0
    assert details.min_price >= 0.0
    assert np.isclose(details.prices[-1], details.max_price)


def test_quantile_autogrid_uses_only_psm_valid_rows() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10, 11, 12, 13, 14, 9999],
            "bargain": [20, 21, 22, 23, 24, 5],
            "expensive_acceptable": [30, 31, 32, 33, 34, 4],
            "too_expensive": [40, 41, 42, 43, 44, 3],
        }
    )
    details = build_price_grid_details(df, GridConfig(), currency="EUR")

    assert details.method == "quantile"
    assert details.max_price == 100.0


def test_quantile_autogrid_step_calculation_with_snap() -> None:
    rows = []
    for i in range(80):
        rows.append(
            {
                "too_cheap": 200 + i,
                "bargain": 260 + i,
                "expensive_acceptable": 320 + i,
                "too_expensive": 380 + i,
            }
        )
    df = pd.DataFrame(rows)
    details = build_price_grid_details(df, GridConfig(), currency="SEK")

    assert details.method == "quantile"
    assert details.increment == 20.0
    assert details.min_price % 20.0 == 0.0
    assert details.max_price % 20.0 == 0.0
    assert details.step % 20.0 == 0.0
    assert details.step >= 20.0

    step_raw = (details.max_price - details.min_price) / 100.0
    expected_step = _nice_number(step_raw)
    expected_step = max(expected_step, 20.0)
    expected_step = math.ceil(expected_step / 20.0) * 20.0
    assert np.isclose(details.step, expected_step)


def test_quantile_autogrid_falls_back_for_small_samples() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [18, 20, 21],
            "bargain": [25, 28, 29],
            "expensive_acceptable": [34, 36, 37],
            "too_expensive": [42, 45, 47],
        }
    )
    details = build_price_grid_details(df, GridConfig(), currency="EUR")

    assert details.method == "legacy"
    assert details.p05 is None
    assert details.p95 is None
    assert details.min_price == 15.0
    assert details.max_price == 50.0
