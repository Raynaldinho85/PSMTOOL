from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.nms import compute_nms
from psm_tool.core.turnover_index import compute_profit_proxy, compute_turnover_index
from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.psm_plot import make_psm_figure
from psm_tool.plots.render_static import prepare_figure_for_static_export
from psm_tool.plots.turnover_index_plot import make_pi_economics_figure


def _assert_white_background(fig: go.Figure) -> None:
    assert fig.layout.paper_bgcolor == "#ffffff"
    assert fig.layout.plot_bgcolor == "#ffffff"
    assert fig.layout.font.color == "#1f2937"


def _sample_curves() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "price": [10.0, 20.0, 30.0, 40.0],
            "too_cheap": [100.0, 80.0, 40.0, 10.0],
            "bargain": [100.0, 90.0, 55.0, 20.0],
            "expensive": [0.0, 20.0, 50.0, 80.0],
            "too_expensive": [0.0, 15.0, 45.0, 85.0],
            "not_bargain": [0.0, 10.0, 45.0, 80.0],
            "not_expensive": [100.0, 80.0, 50.0, 20.0],
        }
    )


def _nms_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "too_cheap": [10, 10],
            "bargain": [20, 20],
            "expensive_acceptable": [30, 30],
            "too_expensive": [40, 40],
            "pi_bargain_pct": [80, 60],
            "pi_expensive_pct": [40, 30],
            "puki": [1, 2],
        }
    )


def test_psm_figure_has_explicit_white_background() -> None:
    curves = _sample_curves()
    fig = make_psm_figure(curves, compute_psm_kpis(curves))

    _assert_white_background(fig)


def test_nms_figure_has_explicit_white_background() -> None:
    prices = _sample_curves()["price"].to_numpy(dtype=float)
    result = compute_nms(_nms_input(), prices)

    fig = make_nms_figure(result)

    _assert_white_background(fig)


def test_turnover_and_profit_figures_have_explicit_white_background() -> None:
    prices = _sample_curves()["price"].to_numpy(dtype=float)
    nms = compute_nms(_nms_input(), prices)
    turnover = compute_turnover_index(prices, nms.curves["trial_pct"].to_numpy(dtype=float))
    profit = compute_profit_proxy(
        prices,
        turnover.df["purchase_intention_pct"].to_numpy(dtype=float),
        unit_cost=12.0,
    )

    turnover_fig = make_pi_economics_figure(turnover, currency="EUR")
    profit_fig = make_pi_economics_figure(
        turnover,
        currency="EUR",
        mode="profit",
        profit_result=profit,
        unit_cost=12.0,
    )

    _assert_white_background(turnover_fig)
    _assert_white_background(profit_fig)


def test_static_export_preparation_applies_white_theme_to_copy() -> None:
    source = go.Figure()
    source.update_layout(paper_bgcolor="#111111", plot_bgcolor="#222222")

    prepared = prepare_figure_for_static_export(source)

    _assert_white_background(prepared)
    assert source.layout.paper_bgcolor == "#111111"
    assert source.layout.plot_bgcolor == "#222222"
