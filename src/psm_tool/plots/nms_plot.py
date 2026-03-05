from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from psm_tool.core.nms import NMSResult


def make_nms_figure(result: NMSResult) -> go.Figure:
    curves = result.curves
    figure = make_subplots(specs=[[{"secondary_y": True}]])

    figure.add_trace(
        go.Scatter(
            x=curves["price"],
            y=curves["trial_pct"],
            mode="lines",
            name="Trial %",
            line={"color": "#1f77b4"},
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=curves["price"],
            y=curves["revenue_per_100"],
            mode="lines",
            name="Revenue / 100",
            line={"color": "#d62728"},
        ),
        secondary_y=True,
    )

    figure.add_vline(
        x=result.max_trial_price,
        line_dash="dot",
        line_color="#1f77b4",
        annotation_text="MaxTrial",
        annotation_position="top left",
    )
    figure.add_vline(
        x=result.max_revenue_price,
        line_dash="dot",
        line_color="#d62728",
        annotation_text="MaxRevenue",
        annotation_position="top right",
    )

    figure.update_xaxes(title_text="Price")
    figure.update_yaxes(title_text="Trial %", secondary_y=False)
    figure.update_yaxes(title_text="Revenue / 100", secondary_y=True)
    figure.update_layout(
        title={
            "text": "NMS Trial + Revenue",
            "x": 0.0,
            "xanchor": "left",
            "y": 0.99,
            "yanchor": "top",
            "pad": {"t": 0, "b": 30},
        },
        template="plotly_white",
        hovermode="x unified",
        height=500,
        legend={
            "title": {"text": ""},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.01,
            "xanchor": "center",
            "x": 0.5,
        },
        margin={"t": 62, "r": 64, "b": 30, "l": 56},
    )
    return figure
