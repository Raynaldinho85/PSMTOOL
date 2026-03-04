from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from psm_tool.core.metrics import PSMKPIResult


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
    for column, label in (
        ("too_cheap", "Too Cheap"),
        ("bargain", "Bargain"),
        ("expensive", "Expensive"),
        ("too_expensive", "Too Expensive"),
        ("not_bargain", "Not Bargain"),
        ("not_expensive", "Not Expensive"),
    ):
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
        for key, value in (
            ("PMI", kpis.pmi.value),
            ("OPP", kpis.opp.value),
            ("IDP", kpis.idp.value),
            ("PME", kpis.pme.value),
        ):
            fig.add_vline(x=value, line_dash="dot", line_width=1, annotation_text=key)

    fig.update_layout(
        title="Van Westendorp Price Sensitivity Meter",
        xaxis_title="Price",
        yaxis_title="Share (%)",
        legend_title="Curves",
        hovermode="x unified",
        height=500,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        template="plotly_white",
    )
    fig.update_yaxes(range=[0, 100])
    return fig
