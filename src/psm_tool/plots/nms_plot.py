from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from psm_tool.core.nms import NMSResult


def make_nms_figure(result: NMSResult) -> go.Figure:
    curves = result.curves
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=curves["price"], y=curves["trial_pct"], mode="lines", name="Trial %")
    )
    fig.add_trace(
        go.Scatter(
            x=curves["price"], y=curves["turnover_index"], mode="lines", name="Turnover Index"
        )
    )
    fig.add_vline(
        x=result.max_trial_price,
        line_dash="dot",
        line_color="#2f855a",
        annotation_text="MaxTrial",
    )
    fig.add_vline(
        x=result.max_revenue_price,
        line_dash="dot",
        line_color="#c53030",
        annotation_text="MaxRevenue",
    )
    fig.update_layout(
        title="NMS Trial and Revenue Curves",
        xaxis_title="Price",
        yaxis_title="Index / Percent",
        template="plotly_white",
    )
    return fig


def make_nms_frame(curves: pd.DataFrame) -> pd.DataFrame:
    return curves.copy()
