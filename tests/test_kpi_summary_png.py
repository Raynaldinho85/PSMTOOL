from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.turnover_index import compute_turnover_index
from psm_tool.report.kpi_summary_png import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    CARD_BOTTOM_Y,
    CARD_LAYOUTS,
    kpi_summary_png_bytes,
    make_kpi_summary_figure,
)


def _sample_analysis() -> dict:
    curves = pd.DataFrame(
        {
            "price": np.array([10.0, 20.0, 30.0, 40.0]),
            "too_cheap": np.array([100.0, 80.0, 40.0, 10.0]),
            "bargain": np.array([100.0, 90.0, 55.0, 20.0]),
            "expensive": np.array([0.0, 20.0, 50.0, 80.0]),
            "too_expensive": np.array([0.0, 15.0, 45.0, 85.0]),
            "not_bargain": np.array([0.0, 10.0, 45.0, 80.0]),
            "not_expensive": np.array([100.0, 80.0, 50.0, 20.0]),
        }
    )
    turnover = compute_turnover_index(
        curves["price"].to_numpy(dtype=float),
        np.array([25.0, 60.0, 50.0, 20.0], dtype=float),
    )
    kpis = compute_psm_kpis(curves).as_dict()
    return {
        "product_id": "Classic",
        "segment": "DE",
        "currency": "EUR",
        "kpis": kpis,
        "turnover_index_result": turnover,
    }


def _annotation_texts(fig) -> list[str]:
    return [str(annotation.text) for annotation in fig.layout.annotations]


def _bottom_card_x0s(fig) -> list[float]:
    return [
        float(shape.x0) for shape in fig.layout.shapes if float(shape.y0) == float(CARD_BOTTOM_Y)
    ]


def test_kpi_summary_figure_uses_fixed_white_canvas_and_all_cards() -> None:
    fig = make_kpi_summary_figure(_sample_analysis())
    texts = "\n".join(_annotation_texts(fig))

    assert fig.layout.width == CANVAS_WIDTH
    assert fig.layout.height == CANVAS_HEIGHT
    assert fig.layout.paper_bgcolor == "#ffffff"
    assert fig.layout.plot_bgcolor == "#ffffff"
    assert "KPI Summary" in texts
    assert "Product: Classic | Country: DE | Currency: EUR" in texts
    for label in ("PMI", "OPP", "IDP", "PME", "Max Turnover Price"):
        assert f"<b>{label}</b>" in texts
    for term in (
        "Point of Marginal Cheapness",
        "Optimal Price Point",
        "Indifference Price Point",
        "Point of Marginal Expensiveness",
    ):
        assert term in texts
    assert len(fig.layout.shapes) == 5


def test_kpi_summary_uses_centered_five_card_layout_without_tested_price() -> None:
    fig = make_kpi_summary_figure(_sample_analysis())
    texts = "\n".join(_annotation_texts(fig))

    assert len(fig.layout.shapes) == 5
    assert "<b>Tested Price</b>" not in texts
    assert _bottom_card_x0s(fig) == list(CARD_LAYOUTS[5][1])


def test_kpi_summary_adds_symmetric_sixth_card_for_active_valid_tested_price() -> None:
    analysis = _sample_analysis()
    analysis["tested_price"] = 455.4
    analysis["tested_price_active"] = True

    fig = make_kpi_summary_figure(analysis)
    texts = "\n".join(_annotation_texts(fig))

    assert len(fig.layout.shapes) == 6
    assert "<b>Tested Price</b>" in texts
    assert "EUR 455" in texts
    assert "Price tested in study" in texts
    assert _bottom_card_x0s(fig) == list(CARD_LAYOUTS[6][1])


def test_kpi_summary_localizes_tested_price_card_for_german() -> None:
    analysis = _sample_analysis()
    analysis["tested_price"] = 455.4
    analysis["tested_price_active"] = True
    analysis["language"] = "de"

    fig = make_kpi_summary_figure(analysis)
    texts = "\n".join(_annotation_texts(fig))

    assert "<b>Testpreis</b>" in texts
    assert "Testpreis in der Studie" in texts


def test_kpi_summary_localizes_turnover_card_for_german() -> None:
    analysis = _sample_analysis()
    analysis["language"] = "de"

    fig = make_kpi_summary_figure(analysis)
    texts = "\n".join(_annotation_texts(fig))

    assert "<b>Max Umsatz</b>" in texts
    assert "Preis mit höchstem Umsatz" in texts


def test_kpi_summary_ignores_inactive_or_invalid_tested_price() -> None:
    invalid_values = [455.4, 0, -1, "bad", float("nan"), float("inf")]
    active_flags = [False, True, True, True, True, True]

    for tested_price, active in zip(invalid_values, active_flags, strict=True):
        analysis = _sample_analysis()
        analysis["tested_price"] = tested_price
        analysis["tested_price_active"] = active

        fig = make_kpi_summary_figure(analysis)
        texts = "\n".join(_annotation_texts(fig))

        assert len(fig.layout.shapes) == 5
        assert "<b>Tested Price</b>" not in texts
        assert _bottom_card_x0s(fig) == list(CARD_LAYOUTS[5][1])


def test_kpi_summary_figure_renders_integer_interval_and_diagnostic_caveats() -> None:
    analysis = _sample_analysis()
    kpis = dict(analysis["kpis"])
    kpis.update(
        {
            "opp_status": "interval",
            "opp_low": 12.2,
            "opp_high": 18.7,
            "idp_status": "closest",
        }
    )
    analysis["kpis"] = kpis

    texts = "\n".join(_annotation_texts(make_kpi_summary_figure(analysis)))

    assert "EUR 12-19" in texts
    assert ".00" not in texts
    assert "interval estimate" in texts
    assert "diagnostic" in texts


def test_kpi_summary_figure_handles_missing_turnover() -> None:
    analysis = _sample_analysis()
    analysis.pop("turnover_index_result")

    texts = "\n".join(_annotation_texts(make_kpi_summary_figure(analysis)))

    assert "<b>Max Turnover Price</b>" in texts
    assert "Not available for this analysis" in texts


def test_kpi_summary_card_annotations_are_centered_and_overflow_limited() -> None:
    analysis = _sample_analysis()
    analysis["currency"] = "CURRENCYCODETHATISVERYTOOLONG"
    kpis = dict(analysis["kpis"])
    kpis["pmi"] = 12345678901234567890.0
    analysis["kpis"] = kpis

    fig = make_kpi_summary_figure(analysis)
    annotations = [
        annotation
        for annotation in fig.layout.annotations
        if str(annotation.text).startswith("<b>PMI</b>")
        or str(annotation.text).startswith("<b>CURRENCYCODE")
        or "Lower bound" in str(annotation.text)
    ]

    assert annotations
    assert all(str(annotation.xanchor) == "center" for annotation in annotations)
    value_texts = [
        str(annotation.text) for annotation in annotations if "CURRENCYCODE" in str(annotation.text)
    ]
    assert value_texts
    assert all("<br>" not in text for text in value_texts)
    assert any(text.endswith("...</b>") for text in value_texts)
    explanation_texts = [
        str(annotation.text) for annotation in annotations if "Lower bound" in str(annotation.text)
    ]
    assert explanation_texts
    assert all(text.count("<br>") <= 1 for text in explanation_texts)


def test_kpi_summary_png_bytes_delegates_to_static_renderer(monkeypatch) -> None:
    captured = {}

    def fake_renderer(fig, **kwargs):
        captured["width"] = fig.layout.width
        captured["annotations"] = len(fig.layout.annotations)
        captured["safe_margins"] = kwargs.get("safe_margins")
        return b"PNG"

    monkeypatch.setattr("psm_tool.report.kpi_summary_png.figure_to_png_bytes", fake_renderer)

    payload = kpi_summary_png_bytes(
        {
            "product_id": "Classic",
            "segment": "DE",
            "currency": "EUR",
            "kpis": {},
            "turnover_index_result": SimpleNamespace(max_turnover_price=20.0),
        }
    )

    assert payload == b"PNG"
    assert captured["width"] == CANVAS_WIDTH
    assert captured["annotations"] > 0
    assert captured["safe_margins"] is False
