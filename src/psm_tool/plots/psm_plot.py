from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from psm_tool.core.metrics import PSMKPIResult


def make_psm_figure(curves: pd.DataFrame, kpis: PSMKPIResult | None = None) -> go.Figure:
    fig = go.Figure()
    for column, label in (
        ("too_cheap", "Too Cheap"),
        ("bargain", "Bargain"),
        ("expensive", "Expensive"),
        ("too_expensive", "Too Expensive"),
        ("not_bargain", "Not Bargain"),
        ("not_expensive", "Not Expensive"),
    ):
        if column in curves.columns:
            fig.add_trace(go.Scatter(x=curves["price"], y=curves[column], mode="lines", name=label))

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
        template="plotly_white",
    )
    return fig
