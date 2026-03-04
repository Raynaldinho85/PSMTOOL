from __future__ import annotations

from typing import Literal

import plotly.graph_objects as go

from psm_tool.core.turnover_index import ProfitProxyResult, TurnoverIndexResult


def _base_layout(fig: go.Figure) -> None:
    fig.update_layout(
        xaxis_title="Price",
        yaxis_title="Index / %",
        yaxis={"range": [0, 100]},
        template="plotly_white",
        hovermode="x unified",
        height=500,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )


def make_pi_economics_figure(
    turnover_result: TurnoverIndexResult,
    *,
    currency: str,
    mode: Literal["turnover", "profit"] = "turnover",
    profit_result: ProfitProxyResult | None = None,
    unit_cost: float | None = None,
) -> go.Figure:
    frame = turnover_result.df
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

    if mode == "profit":
        if profit_result is None:
            raise ValueError("profit_result is required for profit mode.")
        profit_frame = profit_result.df
        fig.add_trace(
            go.Scatter(
                x=profit_frame["price"],
                y=profit_frame["profit_index"],
                mode="lines+markers",
                name="Profit Index",
                line={"color": "#eab308", "width": 2.5},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=frame["price"],
                y=frame["turnover_index"],
                mode="lines",
                name="Turnover Index",
                line={"color": "#f59e0b", "width": 1.5, "dash": "dot"},
                opacity=0.35,
            )
        )
        marker_text = f"Maximum Profit Proxy {profit_result.max_profit_price:.2f} {currency}"
        fig.add_vline(
            x=profit_result.max_profit_price,
            line_dash="dot",
            line_color="#111827",
            annotation_text=marker_text,
            annotation_position="top",
        )
        if unit_cost is not None:
            fig.add_vline(
                x=float(unit_cost),
                line_dash="dash",
                line_color="#b91c1c",
                annotation_text=f"Break-even (Cost) {float(unit_cost):.2f} {currency}",
                annotation_position="bottom",
            )
        fig.update_layout(title="Purchase Intention & Profit Index (0-100)")
    else:
        fig.add_trace(
            go.Scatter(
                x=frame["price"],
                y=frame["turnover_index"],
                mode="lines+markers",
                name="Turnover Index",
                line={"color": "#eab308", "width": 2.5},
            )
        )
        marker_text = f"Maximum Turnover {turnover_result.max_turnover_price:.2f} {currency}"
        fig.add_vline(
            x=turnover_result.max_turnover_price,
            line_dash="dot",
            line_color="#111827",
            annotation_text=marker_text,
            annotation_position="top",
        )
        fig.update_layout(title="Purchase Intention & Turnover Index (0-100)")

    _base_layout(fig)
    return fig


def make_turnover_index_figure(
    result: TurnoverIndexResult,
    *,
    currency: str,
) -> go.Figure:
    return make_pi_economics_figure(result, currency=currency, mode="turnover")
