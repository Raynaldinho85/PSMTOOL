from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import pytest
from pptx import Presentation

from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.plots.render_static import (
    BrowserPreflightError,
    check_kaleido_browser,
    figure_to_png_bytes,
)
from psm_tool.report.excel_export import build_excel_report
from psm_tool.report.pptx_builder import build_pptx_report


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


def _sample_payload() -> dict:
    curves = _sample_curves()
    kpi_result = compute_psm_kpis(curves)
    return {
        "analyses": [
            {
                "product_id": "Classic",
                "segment": "DE",
                "currency": "EUR",
                "curves": curves,
                "kpi_result": kpi_result,
                "kpis": kpi_result.as_dict(),
            }
        ]
    }


def test_plotly_png_render_succeeds_when_browser_available() -> None:
    try:
        check_kaleido_browser()
    except BrowserPreflightError as exc:
        pytest.skip(f"Browser unavailable for kaleido: {exc}")

    fig = go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 1])])
    payload = figure_to_png_bytes(fig)
    assert payload.startswith(b"\x89PNG")
    assert len(payload) > 100


def test_pptx_export_builds_report() -> None:
    try:
        check_kaleido_browser()
    except BrowserPreflightError as exc:
        pytest.skip(f"Browser unavailable for kaleido: {exc}")

    pptx_bytes = build_pptx_report(_sample_payload())
    assert pptx_bytes.startswith(b"PK")

    presentation = Presentation(BytesIO(pptx_bytes))
    assert len(presentation.slides) >= 1


def test_excel_export_contains_expected_sheets() -> None:
    excel_bytes = build_excel_report(_sample_payload())
    workbook = pd.ExcelFile(BytesIO(excel_bytes))
    assert "kpis" in workbook.sheet_names
    assert "curves" in workbook.sheet_names
