from __future__ import annotations

import math

import pandas as pd

from psm_tool.io.price_sanitization import filter_valid_prices, sanitize_negative_price_columns


def test_filter_valid_prices_excludes_negative_values() -> None:
    assert filter_valid_prices([10, 20, -1, 30]) == [10.0, 20.0, 30.0]


def test_filter_valid_prices_all_negative_behaves_like_empty_input() -> None:
    assert filter_valid_prices([-1, -5, -10]) == []

    df = pd.DataFrame({"too_cheap": [-1, -5, -10]})
    sanitized, counts = sanitize_negative_price_columns(df, ["too_cheap"])
    assert counts["too_cheap"] == 3
    assert sanitized["too_cheap"].isna().all()


def test_filter_valid_prices_handles_missing_and_negative_values() -> None:
    output = filter_valid_prices([10, None, -1, 25, float("nan")])
    assert len(output) == 2
    assert math.isclose(output[0], 10.0)
    assert math.isclose(output[1], 25.0)
