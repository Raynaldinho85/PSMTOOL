from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.core.nms import compute_nms
from psm_tool.core.turnover_index import compute_profit_proxy, compute_turnover_index
from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.turnover_index_plot import make_pi_economics_figure


def _nms_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "too_cheap": [12.0, 14.0, 16.0, 15.0],
            "bargain": [22.0, 24.0, 26.0, 25.0],
            "expensive_acceptable": [34.0, 36.0, 38.0, 37.0],
            "too_expensive": [48.0, 50.0, 52.0, 51.0],
            "pi_bargain_pct": [78.0, 80.0, 75.0, 77.0],
            "pi_expensive_pct": [58.0, 60.0, 55.0, 57.0],
            "puki": [1, 1, 2, 1],
        }
    )


def test_nms_plot_matches_psm_like_header_legend_layout() -> None:
    prices = np.arange(10.0, 55.0, 5.0)
    result = compute_nms(_nms_input(), prices, puki_threshold=2)
    fig = make_nms_figure(result)

    assert fig.layout.height == 500
    assert fig.layout.title.text == "NMS Trial + Revenue"
    assert fig.layout.title.x == 0.0
    assert fig.layout.legend.x == 0.5
    assert fig.layout.legend.xanchor == "center"


def test_nms_plot_places_trial_left_and_revenue_right_of_marker() -> None:
    prices = np.arange(10.0, 55.0, 5.0)
    result = compute_nms(_nms_input(), prices, puki_threshold=2)
    fig = make_nms_figure(result)

    annotations = {
        str(annotation.text): str(annotation.xanchor) for annotation in fig.layout.annotations
    }
    assert annotations["MaxTrial"] == "right"
    assert annotations["MaxRevenue"] == "left"


def test_turnover_plot_matches_psm_like_header_legend_layout() -> None:
    prices = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    pi = np.array([18.0, 40.0, 55.0, 45.0, 25.0])
    turnover_result = compute_turnover_index(prices, pi)
    fig = make_pi_economics_figure(turnover_result, currency="EUR", mode="turnover")

    assert fig.layout.height == 500
    assert fig.layout.title.text == "Purchase Intention & Turnover Index (0-100)"
    assert fig.layout.title.x == 0.0
    assert fig.layout.legend.x == 0.5
    assert fig.layout.legend.xanchor == "center"
    assert fig.layout.legend.y == 1.05
    assert fig.layout.xaxis.title.text == "Price"

    annotations = {str(annotation.text): annotation for annotation in fig.layout.annotations}
    turnover_key = next(key for key in annotations if key.startswith("Maximum Turnover "))
    turnover_annotation = annotations[turnover_key]
    assert str(turnover_annotation.xanchor) == "left"
    assert float(turnover_annotation.y) > 1.0


def test_profit_plot_break_even_left_and_max_profit_right() -> None:
    prices = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    pi = np.array([18.0, 40.0, 55.0, 45.0, 25.0])
    turnover_result = compute_turnover_index(prices, pi)
    profit_result = compute_profit_proxy(prices, pi, unit_cost=20.0)
    fig = make_pi_economics_figure(
        turnover_result,
        currency="EUR",
        mode="profit",
        profit_result=profit_result,
        unit_cost=20.0,
    )

    annotations = {str(annotation.text): annotation for annotation in fig.layout.annotations}
    assert str(annotations["Break-even (Cost)"].xanchor) == "right"
    assert str(annotations["Maximum Profit Proxy"].xanchor) == "left"
    assert float(annotations["Break-even (Cost)"].y) > 1.0
    assert float(annotations["Maximum Profit Proxy"].y) > 1.0
