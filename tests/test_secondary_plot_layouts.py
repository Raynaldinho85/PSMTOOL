from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.core.nms import NMSResult, compute_nms
from psm_tool.core.turnover_index import compute_profit_proxy, compute_turnover_index
from psm_tool.plots.benchmarks import PriceBenchmark
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


def test_nms_plot_uses_primary_grid_and_clean_axis_captions() -> None:
    prices = np.arange(10.0, 55.0, 5.0)
    result = compute_nms(_nms_input(), prices, puki_threshold=2)
    fig = make_nms_figure(result)

    assert fig.layout.yaxis.showgrid is True
    assert fig.layout.yaxis2.showgrid is False
    assert fig.layout.yaxis.zeroline is False
    assert fig.layout.yaxis2.zeroline is False
    assert fig.layout.yaxis.title.text == ""
    assert fig.layout.yaxis2.title.text == ""
    assert fig.layout.legend.x == 0.5
    annotation_text = {str(annotation.text) for annotation in fig.layout.annotations}
    assert {"Trial %", "Revenue / 100"}.issubset(annotation_text)


def test_nms_plot_places_trial_left_and_revenue_right_of_marker() -> None:
    prices = np.arange(10.0, 55.0, 5.0)
    result = compute_nms(_nms_input(), prices, puki_threshold=2)
    fig = make_nms_figure(result)

    annotations = {
        str(annotation.text): str(annotation.xanchor) for annotation in fig.layout.annotations
    }
    assert annotations["MaxTrial"] == "right"
    assert annotations["MaxRevenue"] == "left"


def test_nms_plot_localizes_marker_labels_for_german() -> None:
    prices = np.arange(10.0, 55.0, 5.0)
    result = compute_nms(_nms_input(), prices, puki_threshold=2)
    fig = make_nms_figure(result, language="de")

    assert fig.layout.title.text == "NMS Kaufabsicht + Umsatz"
    assert [trace.name for trace in fig.data] == ["Kaufabsicht (%)", "Umsatz / 100"]
    annotations = {str(annotation.text) for annotation in fig.layout.annotations}
    assert {"Kaufabsicht (%)", "Umsatz / 100"}.issubset(annotations)
    assert "Max. Kaufabsicht" in annotations
    assert "Max. Umsatz" in annotations


def test_nms_close_tested_price_cluster_uses_distinct_label_positions() -> None:
    prices = np.arange(10.0, 55.0, 5.0)
    result = compute_nms(_nms_input(), prices, puki_threshold=2)
    fig = make_nms_figure(
        result,
        price_benchmarks=[
            PriceBenchmark(label="Tested Price", price=float(result.max_trial_price) + 1.0)
        ],
    )

    annotations = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"MaxTrial", "MaxRevenue", "Tested Price"}
    }
    positions = {
        (str(annotation.xanchor), round(float(annotation.y), 3))
        for annotation in annotations.values()
    }

    assert set(annotations) == {"MaxTrial", "MaxRevenue", "Tested Price"}
    assert len(positions) >= 2


def test_nms_dense_trial_tested_revenue_cluster_keeps_fixed_baseline() -> None:
    result = NMSResult(
        curves=pd.DataFrame(
            {
                "price": [10.0, 20.0, 30.0, 40.0, 50.0],
                "trial_pct": [10.0, 40.0, 70.0, 65.0, 30.0],
                "revenue_per_100": [100.0, 800.0, 2100.0, 2600.0, 1500.0],
            }
        ),
        max_trial_price=30.0,
        max_revenue_price=32.0,
        base_n=10,
        included_n=10,
        puki_filter_applied=True,
        puki_threshold=2,
        weighting_applied=False,
    )
    fig = make_nms_figure(
        result,
        price_benchmarks=[PriceBenchmark(label="Tested Price", price=31.0)],
    )
    labels = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"MaxTrial", "MaxRevenue", "Tested Price"}
    }

    assert set(labels) == {"MaxTrial", "MaxRevenue", "Tested Price"}
    assert {round(float(annotation.y), 3) for annotation in labels.values()} == {1.004}


def test_nms_manual_label_side_overrides_use_marker_keys() -> None:
    prices = np.arange(10.0, 55.0, 5.0)
    result = compute_nms(_nms_input(), prices, puki_threshold=2)
    fig = make_nms_figure(
        result,
        price_benchmarks=[
            PriceBenchmark(
                label="Tested Price",
                price=float(result.max_trial_price) + 1.0,
                key="tested_price",
            )
        ],
        label_side_overrides={"max_trial": "right", "tested_price": "left"},
    )

    annotations = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"MaxTrial", "Tested Price"}
    }
    assert str(annotations["MaxTrial"].xanchor) == "left"
    assert str(annotations["Tested Price"].xanchor) == "right"


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


def test_turnover_long_label_and_tested_price_keep_fixed_baseline_when_close() -> None:
    prices = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    pi = np.array([18.0, 40.0, 55.0, 45.0, 25.0])
    turnover_result = compute_turnover_index(prices, pi)
    fig = make_pi_economics_figure(
        turnover_result,
        currency="EUR",
        mode="turnover",
        price_benchmarks=[
            PriceBenchmark(
                label="Tested Price",
                price=float(turnover_result.max_turnover_price) + 1.0,
            )
        ],
    )

    annotations = {str(annotation.text): annotation for annotation in fig.layout.annotations}
    turnover_key = next(key for key in annotations if key.startswith("Maximum Turnover "))
    turnover_annotation = annotations[turnover_key]
    tested_annotation = annotations["Tested Price"]

    assert str(turnover_annotation.xanchor) != str(tested_annotation.xanchor)
    assert float(turnover_annotation.y) == 1.004
    assert float(tested_annotation.y) == 1.004


def test_turnover_manual_label_side_overrides_use_marker_keys() -> None:
    prices = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    pi = np.array([18.0, 40.0, 55.0, 45.0, 25.0])
    turnover_result = compute_turnover_index(prices, pi)
    fig = make_pi_economics_figure(
        turnover_result,
        currency="EUR",
        mode="turnover",
        price_benchmarks=[
            PriceBenchmark(
                label="Tested Price",
                price=float(turnover_result.max_turnover_price) + 1.0,
                key="tested_price",
            )
        ],
        label_side_overrides={"max_turnover_price": "left", "tested_price": "left"},
    )

    annotations = {str(annotation.text): annotation for annotation in fig.layout.annotations}
    turnover_key = next(key for key in annotations if key.startswith("Maximum Turnover "))
    assert str(annotations[turnover_key].xanchor) == "right"
    assert str(annotations["Tested Price"].xanchor) == "right"


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


def test_profit_plot_localizes_title_and_legend_for_german() -> None:
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
        language="de",
    )

    assert fig.layout.title.text == "Kaufabsicht & Profit-Index (0-100)"
    assert [trace.name for trace in fig.data[:2]] == ["Kaufabsicht", "Profit-Index"]
