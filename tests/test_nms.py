from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.core.nms import compute_nms


def test_nms_piecewise_curve_and_max_points() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10],
            "bargain": [20],
            "expensive_acceptable": [30],
            "too_expensive": [40],
            "pi_bargain_pct": [80],
            "pi_expensive_pct": [40],
            "puki": [1],
        }
    )
    prices = np.array([10, 15, 20, 25, 30, 35, 40], dtype=float)
    result = compute_nms(df, prices, puki_threshold=2)

    assert result.curves["trial_pct"].tolist() == [0.0, 40.0, 80.0, 60.0, 40.0, 20.0, 0.0]
    assert np.isclose(result.max_trial_price, 20.0)
    assert np.isclose(result.max_revenue_price, 20.0)
    assert result.included_n == 1
    assert result.puki_filter_applied is True


def test_nms_puki_threshold_controls_population() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10, 10],
            "bargain": [20, 20],
            "expensive_acceptable": [30, 30],
            "too_expensive": [40, 40],
            "pi_bargain_pct": [80, 20],
            "pi_expensive_pct": [40, 10],
            "puki": [1, 3],
        }
    )
    prices = np.array([20], dtype=float)

    strict = compute_nms(df, prices, puki_threshold=2)
    neutral = compute_nms(df, prices, puki_threshold=3)

    assert np.isclose(strict.curves["trial_pct"].iloc[0], 80.0)
    assert np.isclose(neutral.curves["trial_pct"].iloc[0], 50.0)
    assert strict.included_n == 1
    assert neutral.included_n == 2


def test_nms_without_puki_uses_all_respondents() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10, 10],
            "bargain": [20, 20],
            "expensive_acceptable": [30, 30],
            "too_expensive": [40, 40],
            "pi_bargain_pct": [80, 20],
            "pi_expensive_pct": [40, 10],
        }
    )
    result = compute_nms(df, np.array([20], dtype=float))

    assert result.puki_filter_applied is False
    assert result.puki_threshold is None
    assert result.included_n == 2
    assert result.filter_note is not None
