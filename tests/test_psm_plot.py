from __future__ import annotations

import pandas as pd

from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.plots.psm_plot import make_psm_figure, resolve_opp_idp_label_sides


def _sample_curves() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "price": [10.0, 20.0, 30.0, 40.0],
            "too_cheap": [90.0, 70.0, 30.0, 10.0],
            "bargain": [95.0, 80.0, 45.0, 20.0],
            "expensive": [5.0, 20.0, 55.0, 80.0],
            "too_expensive": [0.0, 15.0, 50.0, 85.0],
            "not_bargain": [5.0, 20.0, 55.0, 80.0],
            "not_expensive": [95.0, 80.0, 45.0, 20.0],
        }
    )


def _positive_stress_curves() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "price": [10.0, 20.0, 30.0, 40.0],
            "too_cheap": [90.0, 70.0, 30.0, 10.0],
            "bargain": [70.0, 55.0, 25.0, 10.0],
            "expensive": [10.0, 30.0, 65.0, 90.0],
            "too_expensive": [0.0, 15.0, 50.0, 85.0],
            "not_bargain": [30.0, 45.0, 75.0, 90.0],
            "not_expensive": [90.0, 70.0, 35.0, 10.0],
        }
    )


def test_psm_vertical_marker_labels_are_right_of_lines_and_above_plot() -> None:
    curves = _sample_curves()
    kpis = compute_psm_kpis(curves)
    fig = make_psm_figure(curves, kpis)

    label_annotations = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"PMI", "OPP", "IDP", "PME"}
    }
    assert set(label_annotations.keys()) == {"PMI", "OPP", "IDP", "PME"}
    side_rules = resolve_opp_idp_label_sides(float(kpis.opp.value), float(kpis.idp.value))
    expected_anchor = {"left": "right", "right": "left"}
    y_values: set[float] = set()
    for annotation in label_annotations.values():
        label = str(annotation.text)
        if label in {"OPP", "IDP"}:
            side = "opp" if label == "OPP" else "idp"
            assert str(annotation.xanchor) == expected_anchor[side_rules[side]]
        else:
            assert str(annotation.xanchor) == "left"
        assert float(annotation.y) > 1.0
        y_values.add(float(annotation.y))
    assert len(y_values) == 1


def test_resolve_opp_idp_label_sides_large_positive_stress_flips_lower_left() -> None:
    sides = resolve_opp_idp_label_sides(opp=120.0, idp=100.0)
    assert sides == {"opp": "right", "idp": "left"}


def test_resolve_opp_idp_label_sides_large_negative_stress_flips_lower_left() -> None:
    sides = resolve_opp_idp_label_sides(opp=90.0, idp=100.0)
    assert sides == {"opp": "left", "idp": "right"}


def test_resolve_opp_idp_label_sides_small_stress_keeps_both_right() -> None:
    sides = resolve_opp_idp_label_sides(opp=103.0, idp=100.0)
    assert sides == {"opp": "right", "idp": "right"}


def test_psm_legend_title_is_hidden() -> None:
    fig = make_psm_figure(_sample_curves(), compute_psm_kpis(_sample_curves()))
    if fig.layout.legend and fig.layout.legend.title:
        legend_title = fig.layout.legend.title.text
    else:
        legend_title = None
    assert legend_title in (None, "")


def test_psm_legend_order_matches_price_progression() -> None:
    fig = make_psm_figure(_sample_curves(), compute_psm_kpis(_sample_curves()))
    legend_names = [str(trace.name) for trace in fig.data]
    assert legend_names == [
        "Too Cheap",
        "Bargain",
        "Not Expensive",
        "Not Bargain",
        "Expensive",
        "Too Expensive",
    ]


def test_psm_adds_background_ranges_between_kpi_markers() -> None:
    curves = _sample_curves()
    fig = make_psm_figure(curves, compute_psm_kpis(curves))

    rect_shapes = [shape for shape in fig.layout.shapes if str(shape.type) == "rect"]
    assert len(rect_shapes) >= 3


def test_psm_price_stress_background_is_red_for_negative_stress() -> None:
    curves = _sample_curves()
    fig = make_psm_figure(curves, compute_psm_kpis(curves))
    fills = [str(shape.fillcolor) for shape in fig.layout.shapes if str(shape.type) == "rect"]
    assert "rgba(239, 68, 68, 0.15)" in fills


def test_psm_price_stress_background_is_green_for_positive_stress() -> None:
    curves = _positive_stress_curves()
    fig = make_psm_figure(curves, compute_psm_kpis(curves))
    fills = [str(shape.fillcolor) for shape in fig.layout.shapes if str(shape.type) == "rect"]
    assert "rgba(34, 197, 94, 0.15)" in fills
