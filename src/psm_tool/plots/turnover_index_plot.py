from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

import plotly.graph_objects as go

from psm_tool.core.turnover_index import ProfitProxyResult, TurnoverIndexResult
from psm_tool.i18n.runtime import tr
from psm_tool.plots.benchmarks import PriceBenchmark, add_vertical_price_markers
from psm_tool.plots.style import apply_white_chart_theme


def _base_layout(fig: go.Figure, *, language: str | None = None) -> None:
    fig.update_layout(
        xaxis_title=tr("Price", language),
        yaxis_title=tr("Index / %", language),
        yaxis={"range": [0, 100]},
        hovermode="x unified",
        height=500,
        legend={
            "title": {"text": ""},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.05,
            "xanchor": "center",
            "x": 0.5,
        },
        margin={"t": 82, "r": 20, "b": 30, "l": 56},
    )
    apply_white_chart_theme(fig)


def make_pi_economics_figure(
    turnover_result: TurnoverIndexResult,
    *,
    currency: str,
    mode: Literal["turnover", "profit"] = "turnover",
    profit_result: ProfitProxyResult | None = None,
    unit_cost: float | None = None,
    price_benchmarks: list[PriceBenchmark] | None = None,
    label_side_overrides: Mapping[str, Literal["left", "right"]] | None = None,
    language: str | None = None,
) -> go.Figure:
    frame = turnover_result.df
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=frame["price"],
            y=frame["purchase_intention_pct"],
            mode="lines+markers",
            name=tr("Purchase Intention", language),
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
                name=tr("Profit Index", language),
                line={"color": "#eab308", "width": 2.5},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=frame["price"],
                y=frame["turnover_index"],
                mode="lines",
                name=tr("Turnover Index", language),
                line={"color": "#f59e0b", "width": 1.5, "dash": "dot"},
                opacity=0.35,
            )
        )
        markers = [
            PriceBenchmark(
                label=tr("Maximum Profit Proxy", language),
                price=float(profit_result.max_profit_price),
                color="#111827",
                line_dash="dot",
                line_width=1,
            )
        ]
        if unit_cost is not None:
            markers.append(
                PriceBenchmark(
                    label=tr("Break-even (Cost)", language),
                    price=float(unit_cost),
                    color="#b91c1c",
                    line_dash="dash",
                    line_width=1,
                    preferred_side="left",
                )
            )
        add_vertical_price_markers(fig, [*markers, *(price_benchmarks or [])])
        fig.update_layout(title=tr("Purchase Intention & Profit Index (0-100)", language))
    else:
        fig.add_trace(
            go.Scatter(
                x=frame["price"],
                y=frame["turnover_index"],
                mode="lines+markers",
                name=tr("Turnover Index", language),
                line={"color": "#eab308", "width": 2.5},
            )
        )
        marker_text = tr(
            "Maximum Turnover {price:.2f} {currency}",
            language,
            price=float(turnover_result.max_turnover_price),
            currency=currency,
        )
        add_vertical_price_markers(
            fig,
            [
                PriceBenchmark(
                    label=marker_text,
                    price=float(turnover_result.max_turnover_price),
                    key="max_turnover_price",
                    color="#111827",
                    line_dash="dot",
                    line_width=1,
                ),
                *(price_benchmarks or []),
            ],
            label_side_overrides=label_side_overrides,
        )
        fig.update_layout(title=tr("Purchase Intention & Turnover Index (0-100)", language))

    if fig.layout.title and fig.layout.title.text:
        fig.update_layout(
            title={
                "text": str(fig.layout.title.text),
                "x": 0.0,
                "xanchor": "left",
                "y": 0.99,
                "yanchor": "top",
                "pad": {"t": 0, "b": 30},
            }
        )

    _base_layout(fig, language=language)
    return fig


def make_turnover_index_figure(
    result: TurnoverIndexResult,
    *,
    currency: str,
    price_benchmarks: list[PriceBenchmark] | None = None,
    label_side_overrides: Mapping[str, Literal["left", "right"]] | None = None,
    language: str | None = None,
) -> go.Figure:
    return make_pi_economics_figure(
        result,
        currency=currency,
        mode="turnover",
        price_benchmarks=price_benchmarks,
        label_side_overrides=label_side_overrides,
        language=language,
    )
