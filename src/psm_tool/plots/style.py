from __future__ import annotations

import plotly.graph_objects as go

WHITE = "#ffffff"
TEXT_COLOR = "#1f2937"


def apply_white_chart_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font={"color": TEXT_COLOR},
    )
    return fig
