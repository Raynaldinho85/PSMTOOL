from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.core.nms import compute_nms
from psm_tool.core.turnover_index import compute_turnover_index
from psm_tool.io.validate import validate_template


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
    assert result.weighting_applied is False


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


def test_nms_weight_fallback_for_invalid_weight_column() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10, 10],
            "bargain": [20, 20],
            "expensive_acceptable": [30, 30],
            "too_expensive": [40, 40],
            "pi_bargain_pct": [80, 20],
            "pi_expensive_pct": [40, 10],
            "puki": [1, 1],
            "weight": [0, None],
        }
    )
    weighted = compute_nms(df, np.array([20.0], dtype=float), weight_col="weight")
    unweighted = compute_nms(df, np.array([20.0], dtype=float), weight_col=None)
    assert weighted.weighting_applied is False
    assert np.isclose(weighted.curves["trial_pct"].iloc[0], unweighted.curves["trial_pct"].iloc[0])


def test_nms_fraction_pi_matches_percent_pi_after_validation() -> None:
    percent_df = pd.DataFrame(
        {
            "too_cheap": [10, 12],
            "bargain": [20, 22],
            "expensive_acceptable": [30, 32],
            "too_expensive": [40, 42],
            "pi_bargain_pct": [80.0, 82.0],
            "pi_expensive_pct": [60.0, 58.0],
            "puki": [1, 2],
            "weight": [1.0, 1.0],
            "respondent_id": ["A", "B"],
            "segment": ["DE", "DE"],
            "currency": ["EUR", "EUR"],
            "product_id": ["X", "X"],
        }
    )
    fraction_df = percent_df.copy()
    fraction_df["pi_bargain_pct"] = fraction_df["pi_bargain_pct"] / 100.0
    fraction_df["pi_expensive_pct"] = fraction_df["pi_expensive_pct"] / 100.0

    percent_valid = validate_template(percent_df).normalized_df
    fraction_result = validate_template(fraction_df)
    assert any("PI unit normalized" in warning for warning in fraction_result.warnings)
    fraction_valid = fraction_result.normalized_df

    prices = np.array([10, 15, 20, 25, 30, 35, 40], dtype=float)
    percent_nms = compute_nms(percent_valid, prices, weight_col="weight", puki_threshold=2)
    fraction_nms = compute_nms(fraction_valid, prices, weight_col="weight", puki_threshold=2)

    assert np.allclose(
        percent_nms.curves["trial_pct"].to_numpy(dtype=float),
        fraction_nms.curves["trial_pct"].to_numpy(dtype=float),
        atol=0.1,
    )

    percent_turnover = compute_turnover_index(
        prices, percent_nms.curves["trial_pct"].to_numpy(dtype=float)
    )
    fraction_turnover = compute_turnover_index(
        prices, fraction_nms.curves["trial_pct"].to_numpy(dtype=float)
    )
    assert np.isclose(percent_turnover.max_turnover_index, 100.0)
    assert np.isclose(fraction_turnover.max_turnover_index, 100.0)
    assert np.isclose(percent_turnover.max_turnover_price, fraction_turnover.max_turnover_price)


def test_nms_rejects_mixed_pi_units_in_defensive_path() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10],
            "bargain": [20],
            "expensive_acceptable": [30],
            "too_expensive": [40],
            "pi_bargain_pct": [0.8],
            "pi_expensive_pct": [60.0],
            "puki": [1],
        }
    )
    with np.testing.assert_raises_regex(ValueError, "Mixed PI units detected"):
        compute_nms(df, np.array([20.0], dtype=float), puki_threshold=2)


def test_nms_code11_pi_matches_equivalent_percent_pi() -> None:
    percent_df = pd.DataFrame(
        {
            "too_cheap": [10, 12],
            "bargain": [20, 22],
            "expensive_acceptable": [30, 32],
            "too_expensive": [40, 42],
            "pi_bargain_pct": [73.0, 91.0],  # equivalent to codes 8 and 10
            "pi_expensive_pct": [55.0, 64.0],  # equivalent to codes 6 and 7
            "puki": [1, 2],
            "weight": [1.0, 1.0],
        }
    )
    code_df = percent_df.copy()
    code_df["pi_bargain_pct"] = [8.0, 10.0]
    code_df["pi_expensive_pct"] = [6.0, 7.0]

    prices = np.array([10, 15, 20, 25, 30, 35, 40], dtype=float)
    percent_nms = compute_nms(percent_df, prices, weight_col="weight", puki_threshold=2)
    code_nms = compute_nms(code_df, prices, weight_col="weight", puki_threshold=2)

    assert (
        code_nms.pi_unit_note is not None
        and "detected coded scale (1..11)" in code_nms.pi_unit_note
    )
    assert np.allclose(
        percent_nms.curves["trial_pct"].to_numpy(dtype=float),
        code_nms.curves["trial_pct"].to_numpy(dtype=float),
        atol=0.2,
    )
    assert np.isclose(percent_nms.max_trial_price, code_nms.max_trial_price)
    assert np.isclose(percent_nms.max_revenue_price, code_nms.max_revenue_price)

    percent_turnover = compute_turnover_index(
        prices, percent_nms.curves["trial_pct"].to_numpy(dtype=float)
    )
    code_turnover = compute_turnover_index(
        prices, code_nms.curves["trial_pct"].to_numpy(dtype=float)
    )
    assert np.isclose(percent_turnover.max_turnover_price, code_turnover.max_turnover_price)
