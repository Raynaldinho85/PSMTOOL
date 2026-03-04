from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.core.curves import compute_psm_curves


def _curve_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "too_cheap": [10, 20],
            "bargain": [20, 30],
            "expensive_acceptable": [30, 40],
            "too_expensive": [40, 50],
            "weight": [3, 1],
        }
    )


def test_compute_curves_unweighted_values_match_expected() -> None:
    prices = np.array([10, 20, 30, 40, 50], dtype=float)
    curves = compute_psm_curves(_curve_df(), prices)

    assert curves["too_cheap"].tolist() == [100.0, 50.0, 0.0, 0.0, 0.0]
    assert curves["bargain"].tolist() == [100.0, 100.0, 50.0, 0.0, 0.0]
    assert curves["expensive"].tolist() == [0.0, 0.0, 50.0, 100.0, 100.0]
    assert curves["too_expensive"].tolist() == [0.0, 0.0, 0.0, 50.0, 100.0]
    assert curves["not_bargain"].tolist() == [0.0, 0.0, 50.0, 100.0, 100.0]
    assert curves["not_expensive"].tolist() == [100.0, 100.0, 50.0, 0.0, 0.0]


def test_compute_curves_weighted_values_match_expected() -> None:
    prices = np.array([10, 20, 30, 40, 50], dtype=float)
    curves = compute_psm_curves(_curve_df(), prices, weight_col="weight")

    assert curves["too_cheap"].tolist() == [100.0, 25.0, 0.0, 0.0, 0.0]
    assert curves["too_expensive"].tolist() == [0.0, 0.0, 0.0, 75.0, 100.0]


def test_curves_use_metric_specific_missing_denominator() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10, np.nan],
            "bargain": [20, 30],
            "expensive_acceptable": [30, 40],
            "too_expensive": [40, 50],
        }
    )
    prices = np.array([10, 20], dtype=float)
    curves = compute_psm_curves(df, prices)

    assert curves["too_cheap"].tolist() == [100.0, 0.0]
    assert curves["bargain"].tolist() == [100.0, 100.0]


def test_curves_fallback_to_unweighted_when_weights_invalid() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10, 20],
            "bargain": [20, 30],
            "expensive_acceptable": [30, 40],
            "too_expensive": [40, 50],
            "weight": [0, None],
        }
    )
    prices = np.array([20, 30, 40], dtype=float)
    weighted = compute_psm_curves(df, prices, weight_col="weight")
    unweighted = compute_psm_curves(df, prices, weight_col=None)
    pd.testing.assert_frame_equal(weighted, unweighted)
