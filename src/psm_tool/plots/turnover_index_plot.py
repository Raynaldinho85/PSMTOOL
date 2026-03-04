from __future__ import annotations

import plotly.graph_objects as go

from psm_tool.core.turnover_index import TurnoverIndexResult


def make_turnover_index_figure(
    result: TurnoverIndexResult,
    *,
    currency: str,
) -> go.Figure:
    frame = result.df
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["price"],
            y=frame["purchase_intention_pct"],
            mode="lines+markers",
            name="Purchase Intention",
            line={"color": "#6b7280", "width": 2.5},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["price"],
            y=frame["turnover_index"],
            mode="lines+markers",
            name="Turnover Index",
            line={"color": "#eab308", "width": 2.5},
        )
    )

    marker_text = f"Maximum Turnover {result.max_turnover_price:.2f} {currency}"
    fig.add_vline(
        x=result.max_turnover_price,
        line_dash="dot",
        line_color="#111827",
        annotation_text=marker_text,
        annotation_position="top",
    )

    fig.update_layout(
        title="Purchase Intention & Turnover Index (0-100)",
        xaxis_title="Price",
        yaxis_title="Index / %",
        yaxis={"range": [0, 100]},
        template="plotly_white",
        hovermode="x unified",
        height=500,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )
    return fig
