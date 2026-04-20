from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Literal

import pandas as pd
import plotly.graph_objects as go

from psm_tool.core.metrics import PSMKPIResult
from psm_tool.i18n.runtime import tr
from psm_tool.plots.benchmarks import PriceBenchmark, add_vertical_price_markers
from psm_tool.plots.style import apply_white_chart_theme


def resolve_opp_idp_label_sides(opp: float, idp: float) -> dict[str, str]:
    if not (math.isfinite(float(opp)) and math.isfinite(float(idp))):
        return {"opp": "right", "idp": "right"}
    stress = float(opp) - float(idp)
    if abs(stress) <= 5.0:
        if float(opp) <= float(idp):
            return {"opp": "left", "idp": "right"}
        return {"opp": "right", "idp": "left"}
    if stress > 0:
        return {"opp": "right", "idp": "left"}
    return {"opp": "left", "idp": "right"}


def _annotation_anchor_for_side(side: str) -> tuple[str, int]:
    if side == "left":
        return "right", -6
    return "left", 6


def _add_kpi_range_backgrounds(fig: go.Figure, kpis: PSMKPIResult) -> None:
    points = sorted(
        {
            float(kpis.pmi.value),
            float(kpis.opp.value),
            float(kpis.idp.value),
            float(kpis.pme.value),
        }
    )
    points = [value for value in points if math.isfinite(value)]
    if len(points) < 2:
        return

    fills = [
        "rgba(245, 158, 11, 0.09)",
        "rgba(251, 191, 36, 0.06)",
        "rgba(245, 158, 11, 0.04)",
    ]
    for idx, (left, right) in enumerate(zip(points[:-1], points[1:], strict=False)):
        if right <= left:
            continue
        fig.add_vrect(
            x0=left,
            x1=right,
            fillcolor=fills[idx % len(fills)],
            opacity=1.0,
            line_width=0,
            layer="below",
        )


def _add_price_stress_background(fig: go.Figure, kpis: PSMKPIResult) -> None:
    opp = float(kpis.opp.value)
    idp = float(kpis.idp.value)
    if not (math.isfinite(opp) and math.isfinite(idp)):
        return

    left = min(opp, idp)
    right = max(opp, idp)
    if right <= left:
        return

    if kpis.stress_flag == "positive":
        fill = "rgba(34, 197, 94, 0.15)"
    elif kpis.stress_flag == "negative":
        fill = "rgba(239, 68, 68, 0.15)"
    else:
        fill = "rgba(120, 120, 120, 0.08)"

    fig.add_vrect(
        x0=left,
        x1=right,
        fillcolor=fill,
        opacity=1.0,
        line_width=0,
        layer="below",
    )


def make_psm_figure(
    curves: pd.DataFrame,
    kpis: PSMKPIResult | None = None,
    *,
    price_benchmarks: list[PriceBenchmark] | None = None,
    label_side_overrides: Mapping[str, Literal["left", "right"]] | None = None,
    language: str | None = None,
) -> go.Figure:
    fig = go.Figure()
    palette = {
        "too_cheap": "#2563eb",
        "bargain": "#16a34a",
        "expensive": "#f59e0b",
        "too_expensive": "#dc2626",
        "not_bargain": "#0ea5e9",
        "not_expensive": "#f97316",
    }
    legend_order = (
        ("too_cheap", tr("Too Cheap", language)),
        ("bargain", tr("Bargain", language)),
        ("not_expensive", tr("Not Expensive", language)),
        ("not_bargain", tr("Not Bargain", language)),
        ("expensive", tr("Expensive", language)),
        ("too_expensive", tr("Too Expensive", language)),
    )
    for column, label in legend_order:
        if column in curves.columns:
            fig.add_trace(
                go.Scatter(
                    x=curves["price"],
                    y=curves[column],
                    mode="lines",
                    name=label,
                    line={"width": 2.5, "color": palette[column]},
                )
            )

    if kpis is not None:
        _add_kpi_range_backgrounds(fig, kpis)
        _add_price_stress_background(fig, kpis)
        side_rules = resolve_opp_idp_label_sides(float(kpis.opp.value), float(kpis.idp.value))
        use_close_shift = (
            math.isfinite(float(kpis.price_stress)) and abs(float(kpis.price_stress)) <= 5.0
        )
        psm_markers = [
            PriceBenchmark(
                label="PMI",
                price=float(kpis.pmi.value),
                key="pmi",
                color="#64748b",
                line_dash="dot",
                line_width=1,
            ),
            PriceBenchmark(
                label="OPP",
                price=float(kpis.opp.value),
                key="opp",
                color="#64748b",
                line_dash="dot",
                line_width=1,
                preferred_side=side_rules["opp"],
                label_shift=10 if use_close_shift else 6,
            ),
            PriceBenchmark(
                label="IDP",
                price=float(kpis.idp.value),
                key="idp",
                color="#64748b",
                line_dash="dot",
                line_width=1,
                preferred_side=side_rules["idp"],
                label_shift=10 if use_close_shift else 6,
            ),
            PriceBenchmark(
                label="PME",
                price=float(kpis.pme.value),
                key="pme",
                color="#64748b",
                line_dash="dot",
                line_width=1,
            ),
        ]
        add_vertical_price_markers(
            fig,
            [*psm_markers, *(price_benchmarks or [])],
            label_side_overrides=label_side_overrides,
        )
    elif price_benchmarks:
        add_vertical_price_markers(
            fig,
            price_benchmarks,
            label_side_overrides=label_side_overrides,
        )

    fig.update_layout(
        title={
            "text": tr("Van Westendorp Price Sensitivity Meter", language),
            "x": 0.0,
            "xanchor": "left",
            "y": 0.99,
            "yanchor": "top",
            "pad": {"t": 0, "b": 30},
        },
        xaxis_title=tr("Price", language),
        yaxis_title=tr("Share (%)", language),
        hovermode="x unified",
        height=500,
        legend={
            "title": {"text": ""},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.08,
            "xanchor": "center",
            "x": 0.5,
        },
        margin={"t": 90, "r": 20, "b": 30, "l": 56},
    )
    apply_white_chart_theme(fig)
    fig.update_yaxes(range=[0, 100])
    return fig
