from __future__ import annotations

import html
import math
from dataclasses import dataclass
from typing import Any

import plotly.graph_objects as go

from psm_tool.i18n.runtime import normalize_language, tr
from psm_tool.plots.benchmarks import is_valid_tested_price
from psm_tool.plots.render_static import figure_to_png_bytes
from psm_tool.plots.style import apply_white_chart_theme

CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 900

TEXT = "#111827"
MUTED = "#4b5563"
BORDER = "#d1d5db"
CARD_TOP_Y = 440
CARD_BOTTOM_Y = 150

CARD_LAYOUTS: dict[int, tuple[tuple[float, ...], tuple[float, ...]]] = {
    5: ((85, 585, 1085), (335, 835)),
    6: ((85, 585, 1085), (85, 585, 1085)),
}


@dataclass(frozen=True, slots=True)
class KPISummaryCard:
    label: str
    term: str
    value: str
    explanation: str


KPI_TERMS = {
    "pmi": "Point of Marginal Cheapness",
    "opp": "Optimal Price Point",
    "idp": "Indifference Price Point",
    "pme": "Point of Marginal Expensiveness",
}

KPI_EXPLANATIONS = {
    "pmi": "Lower bound of acceptable range",
    "opp": "Balance point of cheap and expensive",
    "idp": "Balance point of value and expensiveness",
    "pme": "Upper bound of acceptable range",
}

GERMAN_KPI_TERMS = {
    "pmi": "Untere Akzeptanzgrenze",
    "opp": "Optimaler Preispunkt",
    "idp": "Indifferenzpreispunkt",
    "pme": "Obere Akzeptanzgrenze",
}

GERMAN_KPI_EXPLANATIONS = {
    "pmi": "Untere Grenze des akzeptierten Preisbereichs",
    "opp": "Gleichgewichtspunkt zwischen günstig und teuer",
    "idp": "Gleichgewichtspunkt zwischen wertig und teuer",
    "pme": "Obere Grenze des akzeptierten Preisbereichs",
}


def _safe_text(value: Any, fallback: str = "-") -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _format_price(currency: str, value: Any) -> str:
    number = _finite_float(value)
    if number is None:
        return "-"
    return f"{currency} {round(number):.0f}".strip()


def _truncate_line(text: str, max_chars: int) -> str:
    normalized = " ".join(_safe_text(text).split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."


def _wrap_limited(text: str, *, max_lines: int, max_chars_per_line: int) -> str:
    words = " ".join(_safe_text(text).split()).split()
    lines: list[str] = []
    current = ""
    truncated = False
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars_per_line:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if len(lines) >= max_lines:
            truncated = True
            break
        current = _truncate_line(word, max_chars_per_line)
        if len(word) > max_chars_per_line:
            truncated = True
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    elif current:
        truncated = True
    if not lines:
        lines = ["-"]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
    consumed = " ".join(lines).replace("...", "")
    original = " ".join(words)
    if original and len(consumed) < len(original):
        truncated = True
    if truncated and not lines[-1].endswith("..."):
        lines[-1] = _truncate_line(lines[-1], max_chars_per_line)
    return "\n".join(lines[:max_lines])


def _kpi_card(
    kpis: dict[str, Any],
    currency: str,
    key: str,
    label: str,
    *,
    language: str | None,
) -> KPISummaryCard:
    selected_language = normalize_language(language)
    if selected_language == "de":
        base_explanation = GERMAN_KPI_EXPLANATIONS[key]
        term = GERMAN_KPI_TERMS[key]
    else:
        base_explanation = tr(KPI_EXPLANATIONS[key], language)
        term = tr(KPI_TERMS[key], language)
    status = str(kpis.get(f"{key}_status", "closest"))
    value = _finite_float(kpis.get(key))
    if value is None:
        return KPISummaryCard(
            label=tr(label, language),
            term=term,
            value="-",
            explanation=tr("Not available", language),
        )

    if status == "interval":
        low = _finite_float(kpis.get(f"{key}_low"))
        high = _finite_float(kpis.get(f"{key}_high"))
        if low is not None and high is not None:
            display_value = f"{currency} {round(low):.0f}-{round(high):.0f}".strip()
        else:
            display_value = f"{currency} {round(value):.0f}".strip()
        return KPISummaryCard(
            label=tr(label, language),
            term=term,
            value=_truncate_line(display_value, 18),
            explanation=tr(
                "{base_explanation}; interval estimate",
                language,
                base_explanation=base_explanation,
            ),
        )

    if status != "clean":
        return KPISummaryCard(
            label=tr(label, language),
            term=term,
            value=_truncate_line(f"{currency} {round(value):.0f}".strip(), 18),
            explanation=tr(
                "{base_explanation}; diagnostic",
                language,
                base_explanation=base_explanation,
            ),
        )

    return KPISummaryCard(
        label=tr(label, language),
        term=term,
        value=_truncate_line(f"{currency} {round(value):.0f}".strip(), 18),
        explanation=base_explanation,
    )


def _turnover_card(
    analysis: dict[str, Any], currency: str, *, language: str | None
) -> KPISummaryCard:
    selected_language = normalize_language(language)
    turnover = analysis.get("turnover_index_result")
    value = _format_price(currency, getattr(turnover, "max_turnover_price", None))
    label = "Max Umsatz" if selected_language == "de" else "Max Turnover"
    term = "Preis mit höchstem Umsatz" if selected_language == "de" else "Highest turnover price"
    explanation = (
        "Preis mit maximalem Umsatz" if selected_language == "de" else "Price with maximum turnover"
    )
    if value == "-":
        return KPISummaryCard(
            label=label,
            term=term,
            value="-",
            explanation=tr("Not available for this analysis", language),
        )
    return KPISummaryCard(
        label=label,
        term=term,
        value=_truncate_line(value, 18),
        explanation=explanation,
    )


def _tested_price_card(
    analysis: dict[str, Any],
    currency: str,
    *,
    language: str | None,
) -> KPISummaryCard | None:
    if not bool(analysis.get("tested_price_active", False)):
        return None
    tested_price = analysis.get("tested_price")
    if not is_valid_tested_price(tested_price):
        return None
    return KPISummaryCard(
        label=tr("Tested Price", language),
        term="Studien-Benchmark" if normalize_language(language) == "de" else "Study benchmark",
        value=_truncate_line(_format_price(currency, tested_price), 18),
        explanation=(
            "In der Studie getesteter Preis"
            if normalize_language(language) == "de"
            else "Price tested in study"
        ),
    )


def _summary_cards(analysis: dict[str, Any], *, language: str | None) -> list[KPISummaryCard]:
    kpis = dict(analysis.get("kpis") or {})
    currency = _safe_text(analysis.get("currency"), "")
    cards = [
        _kpi_card(kpis, currency, "pmi", "PMI", language=language),
        _kpi_card(kpis, currency, "opp", "OPP", language=language),
        _kpi_card(kpis, currency, "idp", "IDP", language=language),
        _kpi_card(kpis, currency, "pme", "PME", language=language),
        _turnover_card(analysis, currency, language=language),
    ]
    tested_price_card = _tested_price_card(analysis, currency, language=language)
    if tested_price_card is not None:
        cards.append(tested_price_card)
    return cards


def _card_layout_for_count(count: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
    return CARD_LAYOUTS.get(count, CARD_LAYOUTS[5])


def _add_text(
    fig: go.Figure,
    *,
    x: float,
    y: float,
    text: str,
    size: int,
    color: str = TEXT,
    bold: bool = False,
    xanchor: str = "left",
    align: str = "left",
) -> None:
    escaped = "<br>".join(html.escape(line) for line in text.splitlines())
    if bold:
        escaped = f"<b>{escaped}</b>"
    fig.add_annotation(
        x=x,
        y=y,
        text=escaped,
        showarrow=False,
        xanchor=xanchor,
        yanchor="middle",
        align=align,
        font={"size": size, "color": color},
    )


def _add_card(fig: go.Figure, card: KPISummaryCard, *, x0: float, y0: float) -> None:
    card_w = 430
    card_h = 240
    x1 = x0 + card_w
    y1 = y0 + card_h
    fig.add_shape(
        type="rect",
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        line={"color": BORDER, "width": 1.5},
        fillcolor="#ffffff",
        layer="below",
    )
    center_x = x0 + (card_w / 2.0)
    _add_text(
        fig,
        x=center_x,
        y=y1 - 38,
        text=card.label,
        size=24,
        bold=True,
        xanchor="center",
        align="center",
    )
    _add_text(
        fig,
        x=center_x,
        y=y1 - 78,
        text=_truncate_line(card.term, 34),
        size=18,
        color=MUTED,
        xanchor="center",
        align="center",
    )
    _add_text(
        fig,
        x=center_x,
        y=y0 + 116,
        text=_truncate_line(card.value, 18),
        size=42,
        bold=True,
        xanchor="center",
        align="center",
    )
    _add_text(
        fig,
        x=center_x,
        y=y0 + 45,
        text=_wrap_limited(card.explanation, max_lines=2, max_chars_per_line=34),
        size=18,
        color=MUTED,
        xanchor="center",
        align="center",
    )


def make_kpi_summary_figure(analysis: dict[str, Any]) -> go.Figure:
    language = normalize_language(analysis.get("language"))
    product = _safe_text(analysis.get("product_id"))
    country = _safe_text(analysis.get("segment"))
    currency = _safe_text(analysis.get("currency"))
    cards = _summary_cards(analysis, language=language)

    fig = go.Figure()
    fig.update_layout(
        width=CANVAS_WIDTH,
        height=CANVAS_HEIGHT,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        showlegend=False,
    )
    apply_white_chart_theme(fig)
    fig.update_xaxes(
        range=[0, CANVAS_WIDTH],
        visible=False,
        fixedrange=True,
    )
    fig.update_yaxes(
        range=[0, CANVAS_HEIGHT],
        visible=False,
        fixedrange=True,
    )

    _add_text(fig, x=85, y=820, text=tr("KPI Summary", language), size=46, bold=True)
    context = tr(
        "Product: {product} | Country: {country} | Currency: {currency}",
        language,
        product=product,
        country=country,
        currency=currency,
    )
    _add_text(fig, x=85, y=762, text=context, size=24, color=MUTED)

    top_x, bottom_x = _card_layout_for_count(len(cards))
    for card, x0 in zip(cards[:3], top_x, strict=True):
        _add_card(fig, card, x0=x0, y0=CARD_TOP_Y)
    for card, x0 in zip(cards[3:], bottom_x, strict=True):
        _add_card(fig, card, x0=x0, y0=CARD_BOTTOM_Y)

    return fig


def kpi_summary_png_bytes(analysis: dict[str, Any]) -> bytes:
    return figure_to_png_bytes(make_kpi_summary_figure(analysis), safe_margins=False)
