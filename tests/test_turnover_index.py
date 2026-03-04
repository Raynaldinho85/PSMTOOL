from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.core.turnover_index import (
    align_pi_ladder_to_grid,
    compute_profit_proxy,
    compute_turnover_index,
    resolve_purchase_intention_curve,
)


def test_compute_turnover_index_normalizes_and_uses_lowest_price_on_tie() -> None:
    prices = np.array([100.0, 200.0, 400.0], dtype=float)
    pi_pct = np.array([100.0, 50.0, 25.0], dtype=float)
    result = compute_turnover_index(prices, pi_pct)

    assert np.allclose(result.df["turnover_index"].to_numpy(dtype=float), [100.0, 100.0, 100.0])
    assert np.isclose(result.max_turnover_price, 100.0)
    assert np.isclose(result.max_turnover_index, 100.0)


def test_align_pi_ladder_to_grid_interpolates() -> None:
    prices = np.array([100.0, 150.0, 200.0, 250.0, 300.0], dtype=float)
    ladder = pd.DataFrame(
        {
            "price": [100.0, 200.0, 300.0],
            "purchase_intention_pct": [10.0, 50.0, 30.0],
        }
    )
    aligned = align_pi_ladder_to_grid(prices, ladder)
    assert np.allclose(aligned, [10.0, 30.0, 50.0, 40.0, 30.0])


def test_resolve_purchase_intention_curve_falls_back_to_nms_trial() -> None:
    prices = np.array([100.0, 150.0, 200.0], dtype=float)
    nms_curves = pd.DataFrame({"price": [100.0, 200.0], "trial_pct": [20.0, 40.0]})

    pi_curve, source = resolve_purchase_intention_curve(
        prices,
        pi_ladder_df=None,
        nms_curves=nms_curves,
    )
    assert source == "nms_trial"
    assert np.allclose(pi_curve, [20.0, 30.0, 40.0])


def test_compute_profit_proxy_normalizes_and_tie_breaks_lowest_price() -> None:
    prices = np.array([100.0, 200.0, 300.0], dtype=float)
    pi_pct = np.array([100.0, 50.0, 100.0], dtype=float)
    result = compute_profit_proxy(prices, pi_pct, unit_cost=0.0)

    assert np.allclose(
        result.df["profit_proxy_per_100"].to_numpy(dtype=float), [10000.0, 10000.0, 30000.0]
    )
    assert np.isclose(result.max_profit_price, 300.0)
    assert np.isclose(result.max_profit_index, 100.0)

    tie = compute_profit_proxy(
        np.array([100.0, 200.0], dtype=float), np.array([100.0, 50.0]), unit_cost=0.0
    )
    assert np.isclose(tie.max_profit_price, 100.0)


def test_compute_profit_proxy_handles_non_positive_max() -> None:
    prices = np.array([10.0, 20.0, 30.0], dtype=float)
    pi_pct = np.array([0.0, 0.0, 0.0], dtype=float)
    result = compute_profit_proxy(prices, pi_pct, unit_cost=5.0)
    assert np.allclose(result.df["profit_index"].to_numpy(dtype=float), [0.0, 0.0, 0.0])
