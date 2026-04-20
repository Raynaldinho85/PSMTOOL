from __future__ import annotations

import pandas as pd

from psm_tool.core.intersections import IntersectionResult
from psm_tool.core.metrics import PSMKPIResult, compute_psm_kpis
from psm_tool.plots.benchmarks import PriceBenchmark
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
            assert str(annotation.xanchor) in {"left", "right"}
        assert float(annotation.y) > 1.0
        y_values.add(float(annotation.y))
    assert 1 <= len(y_values) <= 3


def test_resolve_opp_idp_label_sides_large_positive_stress_flips_lower_left() -> None:
    sides = resolve_opp_idp_label_sides(opp=120.0, idp=100.0)
    assert sides == {"opp": "right", "idp": "left"}


def test_resolve_opp_idp_label_sides_large_negative_stress_flips_lower_left() -> None:
    sides = resolve_opp_idp_label_sides(opp=90.0, idp=100.0)
    assert sides == {"opp": "left", "idp": "right"}


def test_resolve_opp_idp_label_sides_small_stress_keeps_both_right() -> None:
    sides = resolve_opp_idp_label_sides(opp=103.0, idp=100.0)
    assert sides == {"opp": "right", "idp": "left"}


def _kpis_for_annotation_test(*, opp: float, idp: float) -> PSMKPIResult:
    stress = float(opp - idp)
    if stress > 0:
        stress_flag = "positive"
    elif stress < 0:
        stress_flag = "negative"
    else:
        stress_flag = "neutral"
    return PSMKPIResult(
        pmi=IntersectionResult(value=30.0, status="clean"),
        opp=IntersectionResult(value=float(opp), status="clean"),
        idp=IntersectionResult(value=float(idp), status="clean"),
        pme=IntersectionResult(value=70.0, status="clean"),
        accepted_low=30.0,
        accepted_high=70.0,
        price_stress=stress,
        stress_flag=stress_flag,
    )


def _label_annotations(fig) -> dict[str, object]:
    return {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"PMI", "OPP", "IDP", "PME"}
    }


def test_psm_small_negative_stress_places_smaller_left_and_larger_right() -> None:
    fig = make_psm_figure(_sample_curves(), _kpis_for_annotation_test(opp=47.0, idp=50.0))
    labels = _label_annotations(fig)
    assert str(labels["OPP"].xanchor) == "right"
    assert int(labels["OPP"].xshift) == -10
    assert str(labels["IDP"].xanchor) == "left"
    assert int(labels["IDP"].xshift) == 10
    assert float(labels["OPP"].y) == float(labels["IDP"].y) == float(labels["PMI"].y)


def test_psm_small_positive_stress_places_smaller_left_and_larger_right() -> None:
    fig = make_psm_figure(_sample_curves(), _kpis_for_annotation_test(opp=54.0, idp=50.0))
    labels = _label_annotations(fig)
    assert str(labels["IDP"].xanchor) == "right"
    assert int(labels["IDP"].xshift) == -10
    assert str(labels["OPP"].xanchor) == "left"
    assert int(labels["OPP"].xshift) == 10


def test_psm_large_positive_stress_keeps_existing_annotation_offsets() -> None:
    fig = make_psm_figure(_sample_curves(), _kpis_for_annotation_test(opp=62.0, idp=50.0))
    labels = _label_annotations(fig)
    assert str(labels["IDP"].xanchor) == "right"
    assert int(labels["IDP"].xshift) == -6
    assert str(labels["OPP"].xanchor) == "left"
    assert int(labels["OPP"].xshift) == 6


def test_psm_close_tested_price_keeps_fixed_baseline() -> None:
    fig = make_psm_figure(
        _sample_curves(),
        _kpis_for_annotation_test(opp=47.0, idp=50.0),
        price_benchmarks=[PriceBenchmark(label="Tested Price", price=48.0)],
    )
    annotations = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"OPP", "IDP", "Tested Price"}
    }

    assert set(annotations) == {"OPP", "IDP", "Tested Price"}
    assert len({str(annotation.xanchor) for annotation in annotations.values()}) >= 2
    assert {round(float(annotation.y), 3) for annotation in annotations.values()} == {1.004}


def test_psm_manual_label_side_overrides_use_marker_keys() -> None:
    fig = make_psm_figure(
        _sample_curves(),
        _kpis_for_annotation_test(opp=47.0, idp=50.0),
        price_benchmarks=[PriceBenchmark(label="Tested Price", price=48.0, key="tested_price")],
        label_side_overrides={"pmi": "left", "tested_price": "left"},
    )
    labels = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"PMI", "Tested Price"}
    }

    assert str(labels["PMI"].xanchor) == "right"
    assert str(labels["Tested Price"].xanchor) == "right"


def test_psm_tested_price_uses_fixed_baseline_when_not_truly_close() -> None:
    fig = make_psm_figure(
        _sample_curves(),
        _kpis_for_annotation_test(opp=20.0, idp=35.0),
        price_benchmarks=[PriceBenchmark(label="Tested Price", price=25.0, key="tested_price")],
    )
    labels = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"PMI", "OPP", "IDP", "PME", "Tested Price"}
    }

    assert float(labels["Tested Price"].y) == 1.004
    assert {round(float(annotation.y), 3) for annotation in labels.values()} == {1.004}


def test_psm_tested_price_keeps_fixed_baseline_when_truly_close() -> None:
    fig = make_psm_figure(
        _sample_curves(),
        _kpis_for_annotation_test(opp=27.0, idp=30.0),
        price_benchmarks=[PriceBenchmark(label="Tested Price", price=27.4, key="tested_price")],
    )
    labels = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"OPP", "Tested Price"}
    }

    assert float(labels["OPP"].y) == 1.004
    assert float(labels["Tested Price"].y) == 1.004


def test_psm_pmi_opp_close_pair_keeps_fixed_baseline() -> None:
    kpis = PSMKPIResult(
        pmi=IntersectionResult(value=47.0, status="clean"),
        opp=IntersectionResult(value=48.0, status="clean"),
        idp=IntersectionResult(value=58.0, status="clean"),
        pme=IntersectionResult(value=80.0, status="clean"),
        accepted_low=47.0,
        accepted_high=80.0,
        price_stress=-10.0,
        stress_flag="negative",
    )
    fig = make_psm_figure(_sample_curves(), kpis)
    labels = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"PMI", "OPP"}
    }

    assert float(labels["PMI"].y) == 1.004
    assert float(labels["OPP"].y) == 1.004


def test_psm_right_edge_pme_tested_price_conflict_keeps_fixed_baseline() -> None:
    kpis = PSMKPIResult(
        pmi=IntersectionResult(value=30.0, status="clean"),
        opp=IntersectionResult(value=50.0, status="clean"),
        idp=IntersectionResult(value=60.0, status="clean"),
        pme=IntersectionResult(value=98.0, status="clean"),
        accepted_low=30.0,
        accepted_high=98.0,
        price_stress=-10.0,
        stress_flag="negative",
    )
    fig = make_psm_figure(
        _sample_curves(),
        kpis,
        price_benchmarks=[PriceBenchmark(label="Tested Price", price=97.0)],
    )
    labels = {
        str(annotation.text): annotation
        for annotation in fig.layout.annotations
        if str(annotation.text) in {"PME", "Tested Price"}
    }

    assert str(labels["PME"].xanchor) == "right"
    assert str(labels["Tested Price"].xanchor) == "right"
    assert float(labels["PME"].y) == 1.004
    assert float(labels["Tested Price"].y) == 1.004


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
