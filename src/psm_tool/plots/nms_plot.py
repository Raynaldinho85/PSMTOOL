from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from psm_tool.core.nms import NMSResult
from psm_tool.i18n.runtime import tr
from psm_tool.plots.benchmarks import PriceBenchmark, add_vertical_price_markers
from psm_tool.plots.style import apply_white_chart_theme


def make_nms_figure(
    result: NMSResult,
    *,
    price_benchmarks: list[PriceBenchmark] | None = None,
    label_side_overrides: Mapping[str, Literal["left", "right"]] | None = None,
    language: str | None = None,
) -> go.Figure:
    curves = result.curves
    figure = make_subplots(specs=[[{"secondary_y": True}]])

    figure.add_trace(
        go.Scatter(
            x=curves["price"],
            y=curves["trial_pct"],
            mode="lines",
            name=tr("Trial %", language),
            line={"color": "#1f77b4"},
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=curves["price"],
            y=curves["revenue_per_100"],
            mode="lines",
            name=tr("Revenue / 100", language),
            line={"color": "#d62728"},
        ),
        secondary_y=True,
    )

    add_vertical_price_markers(
        figure,
        [
            PriceBenchmark(
                label=tr("MaxTrial", language),
                price=float(result.max_trial_price),
                key="max_trial",
                color="#1f77b4",
                line_dash="dot",
                line_width=1,
                preferred_side="left",
            ),
            PriceBenchmark(
                label=tr("MaxRevenue", language),
                price=float(result.max_revenue_price),
                key="max_revenue",
                color="#d62728",
                line_dash="dot",
                line_width=1,
                preferred_side="right",
            ),
            *(price_benchmarks or []),
        ],
        label_side_overrides=label_side_overrides,
    )

    figure.update_xaxes(title_text=tr("Price", language))
    figure.update_yaxes(
        title_text="",
        showgrid=True,
        zeroline=False,
        secondary_y=False,
    )
    figure.update_yaxes(
        title_text="",
        showgrid=False,
        zeroline=False,
        secondary_y=True,
    )
    figure.add_annotation(
        xref="paper",
        yref="paper",
        x=0.0,
        y=1.105,
        text=tr("Trial %", language),
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font={"size": 12, "color": "#1f77b4"},
    )
    figure.add_annotation(
        xref="paper",
        yref="paper",
        x=1.0,
        y=1.105,
        text=tr("Revenue / 100", language),
        showarrow=False,
        xanchor="right",
        yanchor="bottom",
        font={"size": 12, "color": "#d62728"},
    )
    figure.update_layout(
        title={
            "text": tr("NMS Trial + Revenue", language),
            "x": 0.0,
            "xanchor": "left",
            "y": 0.99,
            "yanchor": "top",
            "pad": {"t": 0, "b": 30},
        },
        hovermode="x unified",
        height=500,
        legend={
            "title": {"text": ""},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.18,
            "xanchor": "center",
            "x": 0.5,
        },
        margin={"t": 112, "r": 64, "b": 30, "l": 56},
    )
    apply_white_chart_theme(figure)
    return figure
