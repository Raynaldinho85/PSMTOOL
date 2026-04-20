from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.nms import compute_nms
from psm_tool.core.turnover_index import compute_turnover_index
from psm_tool.plots.benchmarks import (
    PriceBenchmark,
    add_vertical_price_markers,
    is_valid_tested_price,
    resolve_marker_label_sides,
)
from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.psm_plot import make_psm_figure
from psm_tool.plots.turnover_index_plot import make_pi_economics_figure


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


def test_tested_price_validation_accepts_only_positive_finite_numbers() -> None:
    assert is_valid_tested_price(1.0)
    assert is_valid_tested_price("2.5")
    assert not is_valid_tested_price(0.0)
    assert not is_valid_tested_price(-1.0)
    assert not is_valid_tested_price("nan")
    assert not is_valid_tested_price("bad")


def test_resolve_marker_label_sides_alternates_close_labels() -> None:
    markers = [
        PriceBenchmark(label="PMI", price=20.0),
        PriceBenchmark(label="Tested Price", price=21.0),
        PriceBenchmark(label="PME", price=60.0),
    ]

    sides = resolve_marker_label_sides(markers, collision_distance=5.0)

    assert sides == ["right", "left", "right"]


def test_add_vertical_price_markers_adds_line_and_label() -> None:
    fig = go.Figure()

    add_vertical_price_markers(fig, [PriceBenchmark(label="Tested Price", price=25.0)])

    assert len(fig.layout.shapes) == 1
    assert fig.layout.shapes[0].x0 == 25.0
    assert any(annotation.text == "Tested Price" for annotation in fig.layout.annotations)


def test_manual_marker_side_override_wins_over_auto_edge_placement() -> None:
    fig = go.Figure(data=[go.Scatter(x=[0.0, 100.0], y=[0.0, 1.0])])

    add_vertical_price_markers(
        fig,
        [PriceBenchmark(label="Right Edge", price=98.0, key="edge", preferred_side="right")],
        label_side_overrides={"edge": "right"},
    )

    annotation = fig.layout.annotations[0]
    assert str(annotation.xanchor) == "left"
    assert int(annotation.xshift) > 0


def test_manual_same_side_close_markers_keep_fixed_baseline() -> None:
    fig = go.Figure(data=[go.Scatter(x=[0.0, 100.0], y=[0.0, 1.0])])

    add_vertical_price_markers(
        fig,
        [
            PriceBenchmark(label="PMI", price=50.0, key="pmi"),
            PriceBenchmark(label="OPP", price=51.0, key="opp"),
        ],
        label_side_overrides={"pmi": "right", "opp": "right"},
    )

    annotations = {str(annotation.text): annotation for annotation in fig.layout.annotations}
    assert str(annotations["PMI"].xanchor) == "left"
    assert str(annotations["OPP"].xanchor) == "left"
    assert float(annotations["PMI"].y) == 1.004
    assert float(annotations["OPP"].y) == 1.004


def test_manual_override_is_not_flipped_by_higher_priority_neighbor() -> None:
    fig = go.Figure(data=[go.Scatter(x=[0.0, 100.0], y=[0.0, 1.0])])

    add_vertical_price_markers(
        fig,
        [
            PriceBenchmark(label="OPP", price=50.0, key="opp", preferred_side="left"),
            PriceBenchmark(label="Tested Price", price=53.2, key="tested_price"),
        ],
        label_side_overrides={"tested_price": "right"},
    )

    annotations = {str(annotation.text): annotation for annotation in fig.layout.annotations}
    assert str(annotations["Tested Price"].xanchor) == "left"
    assert int(annotations["Tested Price"].xshift) > 0


def test_manual_override_is_isolated_by_marker_key() -> None:
    fig = go.Figure(data=[go.Scatter(x=[0.0, 100.0], y=[0.0, 1.0])])

    add_vertical_price_markers(
        fig,
        [
            PriceBenchmark(label="PMI", price=20.0, key="pmi", preferred_side="right"),
            PriceBenchmark(label="PME", price=80.0, key="pme", preferred_side="right"),
        ],
        label_side_overrides={"pmi": "left"},
    )

    annotations = {str(annotation.text): annotation for annotation in fig.layout.annotations}
    assert str(annotations["PMI"].xanchor) == "right"
    assert str(annotations["PME"].xanchor) == "left"


def test_dense_marker_cluster_keeps_fixed_label_baseline() -> None:
    fig = go.Figure(data=[go.Scatter(x=[0.0, 100.0], y=[0.0, 1.0])])

    add_vertical_price_markers(
        fig,
        [
            PriceBenchmark(label="PMI", price=50.0),
            PriceBenchmark(label="OPP", price=51.0),
            PriceBenchmark(label="Tested Price", price=52.0),
        ],
    )

    annotations = list(fig.layout.annotations)
    assert {round(float(annotation.y), 3) for annotation in annotations} == {1.004}


def test_edge_markers_prefer_inward_label_placement() -> None:
    fig = go.Figure(data=[go.Scatter(x=[0.0, 100.0], y=[0.0, 1.0])])

    add_vertical_price_markers(
        fig,
        [
            PriceBenchmark(label="Left Edge", price=2.0, preferred_side="left"),
            PriceBenchmark(label="Right Edge", price=98.0, preferred_side="right"),
        ],
    )

    annotations = {str(annotation.text): annotation for annotation in fig.layout.annotations}
    assert str(annotations["Left Edge"].xanchor) == "left"
    assert str(annotations["Right Edge"].xanchor) == "right"


def test_far_apart_marker_labels_keep_base_lane() -> None:
    fig = go.Figure(data=[go.Scatter(x=[0.0, 100.0], y=[0.0, 1.0])])

    add_vertical_price_markers(
        fig,
        [
            PriceBenchmark(label="PMI", price=20.0),
            PriceBenchmark(label="OPP", price=50.0),
            PriceBenchmark(label="PME", price=80.0),
        ],
    )

    y_lanes = {round(float(annotation.y), 3) for annotation in fig.layout.annotations}
    assert y_lanes == {1.004}


def test_psm_figure_includes_tested_price_overlay() -> None:
    curves = _sample_curves()
    kpis = compute_psm_kpis(curves)

    fig = make_psm_figure(
        curves,
        kpis,
        price_benchmarks=[PriceBenchmark(label="Tested Price", price=25.0)],
    )

    assert any(annotation.text == "Tested Price" for annotation in fig.layout.annotations)
    assert len(fig.layout.shapes) >= 5


def test_secondary_figures_include_tested_price_overlay() -> None:
    prices = _sample_curves()["price"].to_numpy(dtype=float)
    nms = compute_nms(_nms_input(), prices)
    turnover = compute_turnover_index(prices, nms.curves["trial_pct"].to_numpy(dtype=float))
    benchmark = [PriceBenchmark(label="Tested Price", price=25.0)]

    nms_fig = make_nms_figure(nms, price_benchmarks=benchmark)
    turnover_fig = make_pi_economics_figure(
        turnover,
        currency="EUR",
        price_benchmarks=benchmark,
    )

    assert any(annotation.text == "Tested Price" for annotation in nms_fig.layout.annotations)
    assert any(annotation.text == "Tested Price" for annotation in turnover_fig.layout.annotations)
