from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from psm_tool.core.metrics import PSMKPIResult


def resolve_opp_idp_label_sides(opp: float, idp: float) -> dict[str, str]:
    if not (math.isfinite(float(opp)) and math.isfinite(float(idp))):
        return {"opp": "right", "idp": "right"}
    stress = float(opp) - float(idp)
    if abs(stress) <= 5.0:
        return {"opp": "right", "idp": "right"}
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


def make_psm_figure(curves: pd.DataFrame, kpis: PSMKPIResult | None = None) -> go.Figure:
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
        ("too_cheap", "Too Cheap"),
        ("bargain", "Bargain"),
        ("not_expensive", "Not Expensive"),
        ("not_bargain", "Not Bargain"),
        ("expensive", "Expensive"),
        ("too_expensive", "Too Expensive"),
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
        marker_points = [
            ("PMI", kpis.pmi.value),
            ("OPP", kpis.opp.value),
            ("IDP", kpis.idp.value),
            ("PME", kpis.pme.value),
        ]
        for _key, value in marker_points:
            fig.add_vline(
                x=value,
                line_dash="dot",
                line_width=1,
            )

        base_y = 1.004
        side_rules = resolve_opp_idp_label_sides(float(kpis.opp.value), float(kpis.idp.value))

        for key, value in marker_points:
            value_float = float(value)
            if key == "OPP":
                side = side_rules["opp"]
            elif key == "IDP":
                side = side_rules["idp"]
            else:
                side = "right"
            xanchor, xshift = _annotation_anchor_for_side(side)
            fig.add_annotation(
                x=value_float,
                y=base_y,
                xref="x",
                yref="paper",
                text=key,
                showarrow=False,
                xanchor=xanchor,
                yanchor="bottom",
                xshift=xshift,
                align="left",
                font={"size": 12, "color": "#64748b"},
            )

    fig.update_layout(
        title={
            "text": "Van Westendorp Price Sensitivity Meter",
            "x": 0.0,
            "xanchor": "left",
            "y": 0.99,
            "yanchor": "top",
            "pad": {"t": 0, "b": 30},
        },
        xaxis_title="Price",
        yaxis_title="Share (%)",
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
        template="plotly_white",
    )
    fig.update_yaxes(range=[0, 100])
    return fig
