from __future__ import annotations

import pandas as pd

from psm_tool.core.outliers import OUTLIER_LEVELS, apply_outlier_filter, compute_quantile_bounds

PRICE_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]


def _with_outlier() -> pd.DataFrame:
    normal = list(range(10, 110))
    return pd.DataFrame(
        {
            "too_cheap": normal + [500],
            "bargain": [x + 10 for x in normal] + [600],
            "expensive_acceptable": [x + 20 for x in normal] + [700],
            "too_expensive": [x + 30 for x in normal] + [8000],
        }
    )


def test_outlier_filter_disabled_keeps_all_rows() -> None:
    df = _with_outlier()
    result = apply_outlier_filter(df, PRICE_COLUMNS, level="medium", enabled=False)
    assert result.enabled is False
    assert result.excluded_n == 0
    assert len(result.filtered_df) == len(df)
    assert result.included_mask.all()


def test_outlier_levels_exclude_monotonic_more_or_equal_rows() -> None:
    df = _with_outlier()
    mild = apply_outlier_filter(df, PRICE_COLUMNS, level="mild", enabled=True)
    medium = apply_outlier_filter(df, PRICE_COLUMNS, level="medium", enabled=True)
    strict = apply_outlier_filter(df, PRICE_COLUMNS, level="strict", enabled=True)
    assert mild.excluded_n <= medium.excluded_n <= strict.excluded_n


def test_outlier_filter_excludes_row_if_any_single_column_is_outlier() -> None:
    normal = list(range(10, 110))
    df = pd.DataFrame(
        {
            "too_cheap": normal + [15],
            "bargain": [x + 10 for x in normal] + [25],
            "expensive_acceptable": [x + 20 for x in normal] + [35],
            "too_expensive": [x + 30 for x in normal] + [9999],
        }
    )
    result = apply_outlier_filter(df, PRICE_COLUMNS, level="strict", enabled=True)
    assert result.excluded_n >= 1
    assert 9999 not in result.filtered_df["too_expensive"].tolist()


def test_outlier_filter_keeps_clean_data() -> None:
    df = pd.DataFrame(
        {
            "too_cheap": [10, 11, 12, 13, 14, 15],
            "bargain": [20, 21, 22, 23, 24, 25],
            "expensive_acceptable": [30, 31, 32, 33, 34, 35],
            "too_expensive": [40, 41, 42, 43, 44, 45],
        }
    )
    result = apply_outlier_filter(df, PRICE_COLUMNS, level="mild", enabled=True)
    assert result.excluded_n == 0
    assert len(result.filtered_df) == len(df)


def test_compute_quantile_bounds_contains_all_columns() -> None:
    df = _with_outlier()
    q_low, q_high = OUTLIER_LEVELS["medium"]
    bounds = compute_quantile_bounds(df, PRICE_COLUMNS, q_low=q_low, q_high=q_high)
    assert list(bounds.index) == PRICE_COLUMNS
    assert {"lower", "upper"} == set(bounds.columns)
    for column in PRICE_COLUMNS:
        assert bounds.loc[column, "lower"] <= bounds.loc[column, "upper"]
