from __future__ import annotations

import math
import re
from html import escape
from typing import Literal

import pandas as pd
import streamlit as st

from psm_tool.config import GridConfig
from psm_tool.core.additional_metrics import MetricResult, compute_additional_metrics
from psm_tool.core.curves import compute_psm_curves, resolve_psm_weights
from psm_tool.core.grid import build_price_grid_details
from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.nms import compute_nms
from psm_tool.core.outliers import apply_outlier_filter
from psm_tool.core.qc import apply_psm_validity_filter, apply_puki_filter, compute_qc_report
from psm_tool.core.turnover_index import (
    compute_profit_proxy,
    compute_turnover_index,
    resolve_purchase_intention_curve,
)
from psm_tool.i18n import get_language, tr
from psm_tool.plots.benchmarks import PriceBenchmark
from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.psm_plot import make_psm_figure
from psm_tool.plots.turnover_index_plot import make_pi_economics_figure
from psm_tool.report.insights import (
    build_nms_summary,
    build_profit_summary,
    build_psm_summary,
    build_turnover_summary,
    describe_turnover_source,
)
from psm_tool.report.kpi_summary_png import make_kpi_summary_figure
from psm_tool.report.wording_policy import can_recommend
from psm_tool.ui.auth import require_auth
from psm_tool.ui.page_nav import render_page_nav_bottom, render_page_nav_top
from psm_tool.ui.results_logic import (
    apply_economics_settings,
    apply_manual_defaults_on_enter,
    apply_manual_grid_settings,
    apply_tested_price_settings,
    parse_tested_price,
)
from psm_tool.ui.style import inject_base_styles, render_notice

PRICE_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]
OUTLIER_LABEL_TO_LEVEL = {"Mild": "mild", "Medium": "medium", "Strict": "strict"}
MARKER_SIDE_OPTIONS = ("Auto", "Left", "Right")
MarkerSide = Literal["left", "right"]


def _build_results_tab_specs(
    *,
    has_turnover: bool,
    has_profit: bool,
    has_nms: bool,
    language: str = "en",
) -> list[tuple[str, str]]:
    tab_specs: list[tuple[str, str]] = [("PSM", "psm")]
    if has_turnover:
        tab_specs.append((tr("Purchase Intention + Turnover Index", language), "turnover"))
    if has_profit:
        tab_specs.append((tr("Profit Index (0-100)", language), "profit"))
    if has_nms:
        tab_specs.append((tr("NMS Trial + Revenue", language), "nms_trial_revenue"))
    tab_specs.append((tr("KPI Summary", language), "kpi_summary"))
    tab_specs.append((tr("Quality Control", language), "quality_control"))
    return tab_specs


def _series_or_default(df: pd.DataFrame, column: str, default: str) -> pd.Series:
    if column in df.columns:
        return df[column].fillna(default).astype(str)
    return pd.Series([default] * len(df), index=df.index)


def _weight_column(df: pd.DataFrame) -> str | None:
    return "weight" if "weight" in df.columns else None


def _build_grid_config(
    mode: str,
    snap_enabled: bool,
    manual_min: float | None,
    manual_max: float | None,
    manual_step: float | None,
) -> GridConfig:
    return GridConfig(
        mode=mode,
        snap_enabled=snap_enabled,
        min_price=manual_min,
        max_price=manual_max,
        step=manual_step,
    )


def _has_nms_columns(df: pd.DataFrame) -> bool:
    required = {"pi_bargain_pct", "pi_expensive_pct"}
    return required.issubset(df.columns)


def _select_pi_ladder_for_group(
    pi_ladder_df: pd.DataFrame | None,
    *,
    segment: str,
    currency: str,
    product_id: str,
) -> pd.DataFrame | None:
    if pi_ladder_df is None or len(pi_ladder_df) == 0:
        return None

    selected = pi_ladder_df.copy()
    if "segment" in selected.columns:
        selected = selected.loc[selected["segment"].astype(str) == str(segment)]
    if "currency" in selected.columns:
        selected = selected.loc[
            selected["currency"].astype(str).str.upper() == str(currency).upper()
        ]
    if "product_id" in selected.columns:
        selected = selected.loc[selected["product_id"].astype(str) == str(product_id)]
    if len(selected) == 0:
        return None
    return selected


def _cost_key(product_id: str, segment: str) -> str:
    product = str(product_id).strip()
    if product:
        return product
    return f"segment::{segment}"


def _selection_key(product_id: str, segment: str) -> str:
    product = str(product_id).strip() or "default_product"
    segment_value = str(segment).strip() or "default_segment"
    return f"{product}::{segment_value}"


def _marker_override_widget_key(selection_key: str, chart_id: str, marker_key: str) -> str:
    return f"marker_label_side::{selection_key}::{chart_id}::{marker_key}"


def _marker_override_store() -> dict[str, dict[str, dict[str, MarkerSide]]]:
    store = st.session_state.setdefault("marker_label_side_overrides_by_key", {})
    return store if isinstance(store, dict) else {}


def _set_marker_override(
    *,
    selection_key: str,
    chart_id: str,
    marker_key: str,
    option: str,
) -> None:
    store = _marker_override_store()
    selection_overrides = dict(store.get(selection_key, {}))
    chart_overrides = dict(selection_overrides.get(chart_id, {}))
    normalized = option.strip().lower()
    if normalized == "left":
        chart_overrides[marker_key] = "left"
    elif normalized == "right":
        chart_overrides[marker_key] = "right"
    else:
        chart_overrides.pop(marker_key, None)

    if chart_overrides:
        selection_overrides[chart_id] = chart_overrides
    else:
        selection_overrides.pop(chart_id, None)
    if selection_overrides:
        store[selection_key] = selection_overrides
    else:
        store.pop(selection_key, None)


def _sync_marker_overrides_from_widgets(
    *,
    selection_key: str,
    marker_options_by_chart: dict[str, list[tuple[str, str]]],
) -> None:
    for chart_id, marker_options in marker_options_by_chart.items():
        for marker_key, _label in marker_options:
            widget_key = _marker_override_widget_key(selection_key, chart_id, marker_key)
            if widget_key in st.session_state:
                _set_marker_override(
                    selection_key=selection_key,
                    chart_id=chart_id,
                    marker_key=marker_key,
                    option=str(st.session_state[widget_key]),
                )


def _store_marker_override_from_widget(
    selection_key: str,
    chart_id: str,
    marker_key: str,
    language: str,
) -> None:
    widget_key = _marker_override_widget_key(selection_key, chart_id, marker_key)
    translated_options = tuple(tr(value, language) for value in MARKER_SIDE_OPTIONS)
    selected = str(st.session_state.get(widget_key, translated_options[0]))
    try:
        option = MARKER_SIDE_OPTIONS[translated_options.index(selected)]
    except ValueError:
        option = selected
    _set_marker_override(
        selection_key=selection_key,
        chart_id=chart_id,
        marker_key=marker_key,
        option=option,
    )


def _marker_label_side_overrides(selection_key: str, chart_id: str) -> dict[str, MarkerSide]:
    store = _marker_override_store()
    selection_overrides = store.get(selection_key, {})
    chart_overrides = selection_overrides.get(chart_id, {})
    return {str(key): value for key, value in chart_overrides.items() if value in {"left", "right"}}


def _render_marker_label_override_controls(
    *,
    selection_key: str,
    chart_id: str,
    marker_options: list[tuple[str, str]],
    language: str,
) -> None:
    if not marker_options:
        return
    with st.expander(tr("Marker label placement", language), expanded=False):
        st.caption(
            tr(
                "Use only when automatic marker label placement still overlaps.",
                language,
            )
        )
        store = _marker_override_store()
        chart_overrides = store.get(selection_key, {}).get(chart_id, {})
        translated_options = tuple(tr(value, language) for value in MARKER_SIDE_OPTIONS)
        for marker_key, label in marker_options:
            current = chart_overrides.get(marker_key)
            current_option = current.capitalize() if current in {"left", "right"} else "Auto"
            index = MARKER_SIDE_OPTIONS.index(current_option)
            widget_key = _marker_override_widget_key(selection_key, chart_id, marker_key)
            if (
                widget_key not in st.session_state
                or st.session_state.get(widget_key) not in translated_options
            ):
                st.session_state[widget_key] = translated_options[index]
            st.selectbox(
                label,
                options=translated_options,
                index=index,
                key=widget_key,
                on_change=_store_marker_override_from_widget,
                args=(selection_key, chart_id, marker_key, language),
            )


def _clear_tested_price_marker_overrides(selection_key: str) -> None:
    for chart_id in ("psm", "turnover", "nms"):
        _set_marker_override(
            selection_key=selection_key,
            chart_id=chart_id,
            marker_key="tested_price",
            option="Auto",
        )
        st.session_state.pop(
            _marker_override_widget_key(selection_key, chart_id, "tested_price"),
            None,
        )


def _on_selection_change(product_key: str, country_key: str) -> None:
    if product_key in st.session_state:
        st.session_state["results_selected_product"] = str(st.session_state[product_key])
    if country_key in st.session_state:
        st.session_state["results_selected_segment"] = str(st.session_state[country_key])


def _render_kpi_card(*, title: str, subtitle: str | None, value: str) -> None:
    subtitle_clean = escape(subtitle) if subtitle else ""
    lens_html = ""
    caution_html = ""
    if subtitle and "[Lens:" in subtitle:
        parts = subtitle.split("]")
        subtitle_clean = escape(parts[-1].strip()) if len(parts) > 1 else escape(subtitle)
        lens_label = subtitle.split("[Lens:", 1)[1].split("]", 1)[0].strip()
        if lens_label:
            lens_html = f"<span class='psm-kpi-badge'>{escape(lens_label)}</span>"
    if subtitle and "[Caution:" in subtitle:
        caution_label = subtitle.split("[Caution:", 1)[1].split("]", 1)[0].strip()
        if caution_label:
            caution_html = (
                f"<span class='psm-kpi-badge psm-kpi-badge--warn'>{escape(caution_label)}</span>"
            )
        subtitle_clean = subtitle_clean.replace(f"[Caution:{caution_label}]", "").strip()
    badges_html = (
        f"<div class='psm-kpi-badges'>{lens_html}{caution_html}</div>"
        if lens_html or caution_html
        else ""
    )
    subtitle_html = (
        f"<div class='psm-kpi-sub'>{subtitle_clean}</div>{badges_html}"
        if subtitle
        else "<div class='psm-kpi-sub psm-kpi-sub--empty'>&nbsp;</div>"
    )
    st.markdown(
        (
            "<div class='psm-kpi-card'>"
            f"<div class='psm-kpi-title'>{escape(title)}</div>"
            f"{subtitle_html}"
            f"<div class='psm-kpi-value'>{escape(value)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _subtitle_with_badges(
    base: str,
    *,
    lens: str,
    caution: str | None = None,
    language: str | None = None,
) -> str:
    caution_label = tr(caution, language) if caution else None
    caution_part = f" [Caution:{caution_label}]" if caution_label else ""
    return f"[Lens:{lens}]{caution_part} ({base})"


def _format_intersection_value(
    kpis: dict[str, float | str],
    *,
    key: str,
    price_symbol: str,
) -> tuple[str, str | None]:
    status = str(kpis.get(f"{key}_status", "closest"))
    value = float(kpis.get(key, float("nan")))
    if status == "clean":
        return f"{price_symbol}{value:.2f}", None
    if status == "interval":
        low = kpis.get(f"{key}_low")
        high = kpis.get(f"{key}_high")
        if low is None or high is None:
            return f"{price_symbol}{value:.2f} (~mid)", "interval"
        return (
            f"[{price_symbol}{float(low):.2f}, {price_symbol}{float(high):.2f}] "
            f"(~ {price_symbol}{value:.2f})",
            "interval",
        )
    return f"{price_symbol}{value:.2f} (diagnostic)", "closest"


def _format_additional_metric_value(
    metric: MetricResult,
    *,
    price_symbol: str,
) -> tuple[str, str | None]:
    if metric.is_stable and metric.value is not None:
        if metric.key in {"price_sensitivity_index", "range_symmetry"}:
            return f"{metric.value:.3f}", None
        if metric.key == "revenue_efficiency":
            return f"{metric.value:+.2f} {price_symbol.strip()}", None
        if metric.key == "profit_feasibility_zone":
            return f"{metric.value:.1f}%", None
        return f"{metric.value:.2f}", None
    return "—", "unstable"


def _build_turnover_summary_safe(
    *,
    turnover_result,
    currency: str,
    segment_label: str,
    source: str | None,
    kpi_statuses: dict[str, str] | None = None,
    language: str | None = None,
) -> list[str]:
    try:
        return build_turnover_summary(
            turnover_result,
            currency=currency,
            segment_label=segment_label,
            source=source,
            kpi_statuses=kpi_statuses,
            language=language,
        )
    except TypeError as exc:
        if "unexpected keyword argument" not in str(exc):
            raise
        return build_turnover_summary(
            turnover_result,
            currency=currency,
            segment_label=segment_label,
            source=source,
        )


def _build_profit_summary_safe(
    *,
    profit_result,
    currency: str,
    segment_label: str,
    product_label: str,
    kpi_statuses: dict[str, str] | None = None,
    language: str | None = None,
) -> list[str]:
    try:
        return build_profit_summary(
            profit_result,
            currency=currency,
            segment_label=segment_label,
            product_label=product_label,
            kpi_statuses=kpi_statuses,
            language=language,
        )
    except TypeError as exc:
        if "unexpected keyword argument" not in str(exc):
            raise
        return build_profit_summary(
            profit_result,
            currency=currency,
            segment_label=segment_label,
            product_label=product_label,
        )


def _render_summary_bullets(summary_lines: list[str], language: str | None = None) -> None:
    if not summary_lines:
        st.markdown(f"- {tr('No summary available.', language)}")
        return
    bullet_text = "\n".join(f"- {_strip_lens_prefix(line)}" for line in summary_lines)
    st.markdown(bullet_text)


def _strip_lens_prefix(line: str) -> str:
    return re.sub(r"^(Perception|Modeled demand|Economics proxy):\s*", "", str(line).strip())


def _render_kpi_cards(
    price_symbol: str,
    kpis: dict[str, float | str],
    additional_metrics: dict[str, MetricResult],
    language: str,
) -> dict[str, dict[str, float | str | bool | None]]:
    pmi_value, pmi_caution = _format_intersection_value(kpis, key="pmi", price_symbol=price_symbol)
    opp_value, opp_caution = _format_intersection_value(kpis, key="opp", price_symbol=price_symbol)
    idp_value, idp_caution = _format_intersection_value(kpis, key="idp", price_symbol=price_symbol)
    pme_value, pme_caution = _format_intersection_value(kpis, key="pme", price_symbol=price_symbol)
    derived_payload: dict[str, dict[str, float | str | bool | None]] = {}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _render_kpi_card(
            title=tr("PMI", language),
            subtitle=_subtitle_with_badges(
                tr("Point of Marginal Inexpensiveness", language),
                lens=tr("Perception", language),
                caution=pmi_caution,
                language=language,
            ),
            value=pmi_value,
        )
    with col2:
        _render_kpi_card(
            title=tr("OPP", language),
            subtitle=_subtitle_with_badges(
                tr("Optimal Pricing Point", language),
                lens=tr("Perception", language),
                caution=opp_caution,
                language=language,
            ),
            value=opp_value,
        )
    with col3:
        _render_kpi_card(
            title=tr("IDP", language),
            subtitle=_subtitle_with_badges(
                tr("Indifference Pricing Point", language),
                lens=tr("Perception", language),
                caution=idp_caution,
                language=language,
            ),
            value=idp_value,
        )
    with col4:
        _render_kpi_card(
            title=tr("PME", language),
            subtitle=_subtitle_with_badges(
                tr("Point of Marginal Expensiveness", language),
                lens=tr("Perception", language),
                caution=pme_caution,
                language=language,
            ),
            value=pme_value,
        )
    st.markdown("<div class='psm-kpi-row-gap'></div>", unsafe_allow_html=True)

    pmi_clean = str(kpis.get("pmi_status", "")) == "clean"
    pme_clean = str(kpis.get("pme_status", "")) == "clean"
    opp_clean = str(kpis.get("opp_status", "")) == "clean"
    idp_clean = str(kpis.get("idp_status", "")) == "clean"

    col5, col6 = st.columns(2)
    with col5:
        if pmi_clean and pme_clean:
            accepted_range_value = (
                f"{price_symbol}{kpis['accepted_low']:.2f} - "
                f"{price_symbol}{kpis['accepted_high']:.2f}"
            )
            accepted_caution = None
            accepted_reason = None
        else:
            accepted_range_value = "—"
            accepted_caution = "unstable"
            accepted_reason = "Requires clean PMI and PME intersections."
        _render_kpi_card(
            title=tr("Accepted Range", language),
            subtitle=_subtitle_with_badges(
                tr("Range consumers find acceptable", language),
                lens=tr("Perception", language),
                caution=accepted_caution,
                language=language,
            ),
            value=accepted_range_value,
        )
        derived_payload["accepted_range"] = {
            "is_stable": accepted_caution is None,
            "display_value": accepted_range_value,
            "diagnostic_value": float(kpis["accepted_high"]) - float(kpis["accepted_low"]),
            "reason": accepted_reason,
            "lens": tr("Perception", language),
        }
    with col6:
        if opp_clean and idp_clean:
            stress_value = f"{kpis['price_stress']:.2f} ({kpis['stress_flag']})"
            stress_caution = None
            stress_reason = None
        else:
            stress_value = "—"
            stress_caution = "unstable"
            stress_reason = "Requires clean OPP and IDP intersections."
        _render_kpi_card(
            title=tr("Price Stress", language),
            subtitle=_subtitle_with_badges(
                tr("Difference between OPP and IDP", language),
                lens=tr("Perception", language),
                caution=stress_caution,
                language=language,
            ),
            value=stress_value,
        )
        derived_payload["price_stress"] = {
            "is_stable": stress_caution is None,
            "display_value": stress_value,
            "diagnostic_value": float(kpis.get("price_stress", 0.0)),
            "reason": stress_reason,
            "lens": tr("Perception", language),
        }
    st.markdown("<div class='psm-kpi-row-gap'></div>", unsafe_allow_html=True)

    col7, col8, col9, col10 = st.columns(4)
    metric_specs = [
        (
            "price_sensitivity_index",
            "Price Sensitivity Index",
            "Relative accepted-range width: (PME - PMI) / IDP",
        ),
        (
            "range_symmetry",
            "Range Symmetry",
            "Right/left accepted-range span around IDP",
        ),
        (
            "revenue_efficiency",
            "Revenue Efficiency",
            "Gap between max turnover price and OPP",
        ),
        (
            "profit_feasibility_zone",
            "Profit Feasibility Zone",
            "Accepted-range share above cost",
        ),
    ]
    for column, (key, title, base_subtitle) in zip(
        (col7, col8, col9, col10),
        metric_specs,
        strict=False,
    ):
        metric = additional_metrics[key]
        metric_value, metric_caution = _format_additional_metric_value(
            metric, price_symbol=price_symbol
        )
        with column:
            _render_kpi_card(
                title=tr(title, language),
                subtitle=_subtitle_with_badges(
                    tr(base_subtitle, language),
                    lens=tr(metric.lens, language),
                    caution=metric_caution,
                    language=language,
                ),
                value=metric_value,
            )
        derived_payload[key] = {
            "is_stable": metric.is_stable,
            "display_value": metric_value,
            "diagnostic_value": metric.diagnostic_value,
            "reason": metric.reason,
            "lens": tr(metric.lens, language),
        }
    st.markdown("<div class='psm-kpi-row-gap'></div>", unsafe_allow_html=True)
    return derived_payload


def _apply_psm_axis_footer(
    figure,
    *,
    selected_product: str,
    selected_segment: str,
    currency: str,
    total_n: int,
    valid_n: int,
    analysis_n: int,
    language: str,
) -> None:
    selection_value = f"{escape(selected_product)} / {escape(selected_segment)}"
    price_value = escape(currency or "n/a")
    analysis_value = (
        f"{analysis_n} ("
        f"{escape(tr('valid', language))}: {valid_n} / "
        f"{escape(tr('total', language))}: {total_n})"
    )

    selection_text = (
        f"<span style='color:#78716c;'>{escape(tr('Selection:', language))}</span> "
        f"<span style='color:#1c1917;'>{selection_value}</span>"
    )
    price_text = (
        f"<span style='color:#78716c;'>{escape(tr('Price:', language))}</span> "
        f"<span style='color:#1c1917;'>{price_value}</span>"
    )
    analysis_text = (
        "<span style='color:#78716c;'>n:</span> "
        f"<span style='color:#1c1917;'>{analysis_value}</span>"
    )

    figure.update_xaxes(title={"text": ""})
    figure.add_annotation(
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.13,
        text=selection_text,
        showarrow=False,
        xanchor="left",
        yanchor="top",
        align="left",
        font={"size": 13, "color": "#1c1917"},
    )
    figure.add_annotation(
        xref="paper",
        yref="paper",
        x=0.5,
        y=-0.13,
        text=price_text,
        showarrow=False,
        xanchor="center",
        yanchor="top",
        align="center",
        font={"size": 13, "color": "#1c1917"},
    )
    figure.add_annotation(
        xref="paper",
        yref="paper",
        x=1.0,
        y=-0.13,
        text=analysis_text,
        showarrow=False,
        xanchor="right",
        yanchor="top",
        align="right",
        font={"size": 13, "color": "#1c1917"},
    )

    current_margin = figure.layout.margin
    margin_l = int(current_margin.l) if current_margin and current_margin.l is not None else 56
    margin_r = int(current_margin.r) if current_margin and current_margin.r is not None else 20
    margin_t = int(current_margin.t) if current_margin and current_margin.t is not None else 88
    margin_b = int(current_margin.b) if current_margin and current_margin.b is not None else 30
    figure.update_layout(
        margin={"l": margin_l, "r": margin_r, "t": margin_t, "b": max(72, margin_b)}
    )


def _render_selection_controls_box(
    *,
    product_values: list[str],
    segment_values: list[str],
    selected_product: str,
    selected_segment: str,
    grid_method: str,
    increment_label: str,
    min_price: float,
    max_price: float,
    step: float,
    p05_label: str,
    p95_label: str,
    product_key: str,
    country_key: str,
    language: str,
) -> None:
    with st.container(border=True):
        header_col, info_col = st.columns([0.93, 0.07])
        with header_col:
            st.subheader(tr("Selection", language))
        with info_col:
            with st.popover("i"):
                st.caption(tr("Grid details", language))
                st.caption(
                    tr(
                        "Method: {grid_method} | Increment: {increment_label}",
                        language,
                        grid_method=grid_method,
                        increment_label=increment_label,
                    )
                )
                st.caption(
                    tr(
                        "Range: {min_price:.2f} to {max_price:.2f}",
                        language,
                        min_price=min_price,
                        max_price=max_price,
                    )
                )
                st.caption(tr("Step: {step:.2f}", language, step=step))
                st.caption(
                    tr(
                        "P05/P95: {p05_label} / {p95_label}",
                        language,
                        p05_label=p05_label,
                        p95_label=p95_label,
                    )
                )
        select_col1, select_col2 = st.columns(2)
        product_index = (
            product_values.index(selected_product) if selected_product in product_values else 0
        )
        country_index = (
            segment_values.index(selected_segment) if selected_segment in segment_values else 0
        )
        if st.session_state.get(product_key) != selected_product:
            st.session_state[product_key] = selected_product
        if st.session_state.get(country_key) != selected_segment:
            st.session_state[country_key] = selected_segment
        select_col1.selectbox(
            tr("Product", language),
            options=product_values,
            index=product_index,
            key=product_key,
            on_change=_on_selection_change,
            args=(product_key, country_key),
        )
        select_col2.selectbox(
            tr("Country", language),
            options=segment_values,
            index=country_index,
            key=country_key,
            on_change=_on_selection_change,
            args=(product_key, country_key),
        )


def _apply_focus_autoscale(
    figure,
    *,
    kpis: dict[str, float | str],
    increment: float | None,
    extra_prices: list[float] | None = None,
) -> None:
    opp = float(kpis.get("opp", float("nan")))
    idp = float(kpis.get("idp", float("nan")))
    if not (math.isfinite(opp) and math.isfinite(idp)):
        return

    midpoint = (opp + idp) / 2.0
    if not math.isfinite(midpoint) or midpoint <= 0:
        return

    axis_max = midpoint * 2.0
    max_kpi = max(
        float(kpis.get("pmi", float("nan"))),
        opp,
        idp,
        float(kpis.get("pme", float("nan"))),
    )
    if math.isfinite(max_kpi):
        axis_max = max(axis_max, max_kpi)
    for price in extra_prices or []:
        if math.isfinite(float(price)):
            axis_max = max(axis_max, float(price))

    if increment is not None and increment > 0:
        axis_max = math.ceil(axis_max / increment) * increment

    axis_max = max(axis_max, 1.0)
    figure.update_xaxes(range=[0.0, float(axis_max)])


def _apply_pair_focus_autoscale(
    figure,
    *,
    first_price: float,
    second_price: float,
    increment: float | None,
    extra_prices: list[float] | None = None,
) -> None:
    if not (math.isfinite(first_price) and math.isfinite(second_price)):
        return

    midpoint = (first_price + second_price) / 2.0
    if not math.isfinite(midpoint) or midpoint <= 0:
        return

    axis_max = first_price + second_price
    axis_max = max(axis_max, first_price, second_price)
    for price in extra_prices or []:
        if math.isfinite(float(price)):
            axis_max = max(axis_max, float(price))
    if increment is not None and increment > 0:
        axis_max = math.ceil(axis_max / increment) * increment
    axis_max = max(axis_max, 1.0)
    figure.update_xaxes(range=[0.0, float(axis_max)])


def _series_max_price(frame: pd.DataFrame, value_col: str) -> float:
    if value_col not in frame.columns or "price" not in frame.columns or len(frame) == 0:
        return float("nan")
    indexed = frame.sort_values("price", ascending=True)
    idx = indexed[value_col].astype(float).idxmax()
    return float(indexed.loc[idx, "price"])


def _estimate_opp_for_manual_default(
    *,
    group_df: pd.DataFrame,
    currency: str,
    snap_enabled: bool,
    plausibility_filter_enabled: bool,
    puki_threshold: int,
    puki_filter_enabled: bool,
    outlier_enabled: bool,
    outlier_level: str,
) -> float:
    valid_df, _ = apply_psm_validity_filter(group_df)
    analysis_base_df = valid_df if plausibility_filter_enabled else group_df.copy()
    analysis_base_df, _puki_mask = apply_puki_filter(
        analysis_base_df,
        puki_threshold=puki_threshold,
        enabled=puki_filter_enabled,
    )
    analysis_df = apply_outlier_filter(
        analysis_base_df,
        columns=PRICE_COLUMNS,
        level=outlier_level,
        enabled=outlier_enabled,
    ).filtered_df
    if len(analysis_df) == 0:
        return 0.0
    try:
        preview_cfg = GridConfig(mode="auto", snap_enabled=snap_enabled)
        preview_grid = build_price_grid_details(analysis_df, preview_cfg, currency=currency)
        preview_curves = compute_psm_curves(
            analysis_df,
            preview_grid.prices,
            weight_col=_weight_column(analysis_df),
        )
        preview_kpis = compute_psm_kpis(preview_curves)
        opp = float(preview_kpis.opp.value)
        if math.isfinite(opp) and opp >= 0:
            return opp
    except Exception:
        return 0.0
    return 0.0


def main() -> None:
    require_auth()
    inject_base_styles(max_width=2800)
    language = get_language()
    st.markdown(
        f'<p class="psm-page-eyebrow">{tr("Analysis Workspace", language)}</p>',
        unsafe_allow_html=True,
    )
    st.title(tr("2. Results", language))
    render_page_nav_top("results")

    df: pd.DataFrame | None = st.session_state.get("psm_input_df")
    if df is None:
        render_notice(
            tr(
                (
                    "No dataset loaded. Run page '1 Upload' first (or again) "
                    "to load data. Upload unlocks Results and Export."
                ),
                language,
            )
        )
        if st.button(
            tr("Go to Upload", language),
            width="stretch",
            key="results_go_upload_btn",
        ):
            st.switch_page("pages/1_upload.py")
        render_page_nav_bottom("results")
        return

    product_values = sorted(_series_or_default(df, "product_id", "default_product").unique())
    if len(product_values) == 0:
        render_notice(tr("No product values available in dataset.", language))
        render_page_nav_bottom("results")
        return
    if st.session_state.get("results_selected_product") not in product_values:
        st.session_state["results_selected_product"] = product_values[0]
    selected_product = str(st.session_state["results_selected_product"])

    product_df = df.loc[
        _series_or_default(df, "product_id", "default_product") == selected_product
    ].copy()
    segment_values = sorted(_series_or_default(product_df, "segment", "default_segment").unique())
    if len(segment_values) == 0:
        render_notice(tr("No country values available for selected product.", language))
        render_page_nav_bottom("results")
        return
    if st.session_state.get("results_selected_segment") not in segment_values:
        st.session_state["results_selected_segment"] = segment_values[0]
    selected_segment = str(st.session_state["results_selected_segment"])

    group_df = product_df.loc[
        _series_or_default(product_df, "segment", "default_segment") == selected_segment
    ].copy()
    if len(group_df) == 0:
        render_notice(tr("No data for selected product/country.", language))
        render_page_nav_bottom("results")
        return

    currency = str(_series_or_default(group_df, "currency", "").iloc[0]).upper()

    with st.container(border=True):
        st.subheader(tr("Analysis Controls", language))
        snap_enabled = st.toggle(tr("Snap to currency increment", language), value=True)
        plausibility_filter_enabled = st.toggle(
            tr("Apply plausibility filter (strict ordering)", language),
            value=True,
            help=tr(
                "Rule: too_cheap < bargain < expensive_acceptable < too_expensive",
                language,
            ),
        )

        outlier_enabled = st.toggle(tr("Outlier filter enabled", language), value=False)
        outlier_option_labels = {
            "Mild": tr("Mild", language),
            "Medium": tr("Medium", language),
            "Strict": tr("Strict", language),
        }
        outlier_label = outlier_option_labels["Medium"]
        if outlier_enabled:
            outlier_label = st.selectbox(
                tr("Outlier level", language),
                options=list(outlier_option_labels.values()),
                index=1,
            )
        outlier_level_key = next(
            key for key, value in outlier_option_labels.items() if value == outlier_label
        )
        outlier_level = OUTLIER_LABEL_TO_LEVEL[outlier_level_key]

        has_puki = "puki" in group_df.columns
        puki_threshold = 2
        if has_puki:
            include_neutral = st.toggle(
                tr("Include neutral PUKI (<=3) in analysis", language),
                value=False,
                key="puki_neutral",
            )
            puki_threshold = 3 if include_neutral else 2
        else:
            st.caption(
                tr("PUKI column missing: analysis population filter is not applied.", language)
            )

        cost_map: dict[str, float] = st.session_state.setdefault("unit_cost_by_product", {})
        economics_enabled_map: dict[str, bool] = st.session_state.setdefault(
            "economics_enabled_by_product", {}
        )
        unit_cost_key = _cost_key(str(selected_product), str(selected_segment))
        economics_toggle_key = f"economics_enabled_draft::{unit_cost_key}"
        unit_cost_input_key = f"unit_cost_input_draft::{unit_cost_key}"
        stored_economics_enabled = bool(economics_enabled_map.get(unit_cost_key, False))
        stored_unit_cost = float(cost_map.get(unit_cost_key, 0.0))
        if economics_toggle_key not in st.session_state:
            st.session_state[economics_toggle_key] = stored_economics_enabled
        if unit_cost_input_key not in st.session_state:
            st.session_state[unit_cost_input_key] = stored_unit_cost

        economics_draft_enabled = st.toggle(tr("Economics", language), key=economics_toggle_key)
        economics_details_visible = economics_draft_enabled or stored_economics_enabled
        economics_submitted = False
        if economics_details_visible:
            with st.form(
                key=f"economics_form::{unit_cost_key}",
                enter_to_submit=False,
                border=False,
            ):
                st.number_input(
                    tr("Unit cost", language),
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    key=unit_cost_input_key,
                    help=tr(
                        (
                            "Same currency as selected country ({currency}). Used "
                            "only for calculations and exports in this session."
                        ),
                        language,
                        currency=currency,
                    ),
                )
                st.caption(tr("Changes take effect after clicking Apply.", language))
                economics_submitted = st.form_submit_button(tr("Apply", language))
        economics_enabled, stored_unit_cost = apply_economics_settings(
            submitted=economics_submitted,
            draft_enabled=bool(st.session_state.get(economics_toggle_key, False)),
            draft_unit_cost=float(st.session_state.get(unit_cost_input_key, 0.0)),
            stored_enabled=stored_economics_enabled,
            stored_unit_cost=stored_unit_cost,
        )
        economics_enabled_map[unit_cost_key] = economics_enabled
        cost_map[unit_cost_key] = stored_unit_cost

        tested_price_map: dict[str, float] = st.session_state.setdefault("tested_price_by_key", {})
        tested_price_active_map: dict[str, bool] = st.session_state.setdefault(
            "tested_price_active_by_key", {}
        )
        tested_price_scope = _selection_key(str(selected_product), str(selected_segment))
        tested_price_input_key = f"tested_price_input_draft::{tested_price_scope}"
        tested_price_active_key = f"tested_price_active_draft::{tested_price_scope}"
        stored_tested_price = tested_price_map.get(tested_price_scope)
        stored_tested_price_active = bool(tested_price_active_map.get(tested_price_scope, False))
        if tested_price_input_key not in st.session_state and stored_tested_price is not None:
            st.session_state[tested_price_input_key] = f"{float(stored_tested_price):g}"
        st.session_state.setdefault(tested_price_input_key, "")
        if tested_price_active_key not in st.session_state:
            st.session_state[tested_price_active_key] = stored_tested_price_active

        st.text_input(
            tr("Tested Price", language),
            key=tested_price_input_key,
            placeholder=tr("Enter price", language),
            help=tr(
                "Positive numeric price to show as a benchmark line on charts.",
                language,
            ),
        )
        tested_price_draft_value = parse_tested_price(
            st.session_state.get(tested_price_input_key, "")
        )
        tested_price_details_visible = (
            tested_price_draft_value is not None
            or stored_tested_price is not None
            or stored_tested_price_active
        )
        tested_price_submitted = False
        if tested_price_details_visible:
            with st.form(
                key=f"tested_price_form::{tested_price_scope}",
                enter_to_submit=False,
                border=False,
            ):
                st.toggle(
                    tr("Show Tested Price", language),
                    key=tested_price_active_key,
                )
                st.caption(tr("Changes take effect after clicking Apply.", language))
                tested_price_submitted = st.form_submit_button(tr("Apply", language))
        tested_price_value, tested_price_active = apply_tested_price_settings(
            submitted=tested_price_submitted,
            raw_value=st.session_state.get(tested_price_input_key, ""),
            requested_active=bool(st.session_state.get(tested_price_active_key, False)),
            stored_price=(float(stored_tested_price) if stored_tested_price is not None else None),
            stored_active=stored_tested_price_active,
        )
        if tested_price_value is None:
            tested_price_map.pop(tested_price_scope, None)
        else:
            tested_price_map[tested_price_scope] = float(tested_price_value)
        tested_price_active_map[tested_price_scope] = bool(tested_price_active)

        opp_for_manual_default = _estimate_opp_for_manual_default(
            group_df=group_df,
            currency=currency,
            snap_enabled=snap_enabled,
            plausibility_filter_enabled=plausibility_filter_enabled,
            puki_threshold=puki_threshold,
            puki_filter_enabled=has_puki,
            outlier_enabled=outlier_enabled,
            outlier_level=outlier_level,
        )

        control_scope = f"{selected_product}::{selected_segment}"
        mode_key = f"results_grid_mode::{control_scope}"
        previous_mode_key = f"results_grid_prev_mode::{control_scope}"
        manual_initialized_key = f"results_manual_initialized::{control_scope}"
        manual_min_key = f"results_manual_min::{control_scope}"
        manual_max_key = f"results_manual_max::{control_scope}"
        manual_step_key = f"results_manual_step::{control_scope}"
        st.session_state.setdefault(mode_key, "auto")
        st.session_state.setdefault(previous_mode_key, "auto")
        st.session_state.setdefault(manual_initialized_key, False)
        st.session_state.setdefault(manual_min_key, 0.0)
        st.session_state.setdefault(manual_max_key, 100.0)
        st.session_state.setdefault(manual_step_key, 5.0)

        mode = st.selectbox(
            tr("Grid mode", language),
            options=[tr("auto", language), tr("manual", language)],
            key=mode_key,
        )
        mode_lookup = {
            tr("auto", language): "auto",
            tr("manual", language): "manual",
        }
        mode = mode_lookup[mode]
        previous_mode = str(st.session_state.get(previous_mode_key, "auto"))
        manual_min_state = float(st.session_state.get(manual_min_key, 0.0))
        manual_max_state = float(st.session_state.get(manual_max_key, 100.0))
        manual_min_state, manual_max_state, manual_initialized = apply_manual_defaults_on_enter(
            mode=mode,
            previous_mode=previous_mode,
            initialized=bool(st.session_state.get(manual_initialized_key, False)),
            manual_min=manual_min_state,
            manual_max=manual_max_state,
            opp=opp_for_manual_default,
        )
        st.session_state[manual_initialized_key] = manual_initialized
        st.session_state[manual_min_key] = manual_min_state
        st.session_state[manual_max_key] = manual_max_state
        st.session_state[previous_mode_key] = mode
        manual_min_draft_key = f"results_manual_min_draft::{control_scope}"
        manual_max_draft_key = f"results_manual_max_draft::{control_scope}"
        manual_step_draft_key = f"results_manual_step_draft::{control_scope}"
        if manual_min_draft_key not in st.session_state or mode != previous_mode:
            st.session_state[manual_min_draft_key] = manual_min_state
        if manual_max_draft_key not in st.session_state or mode != previous_mode:
            st.session_state[manual_max_draft_key] = manual_max_state
        if manual_step_draft_key not in st.session_state or mode != previous_mode:
            st.session_state[manual_step_draft_key] = float(
                st.session_state.get(manual_step_key, 5.0)
            )

        manual_min: float | None = None
        manual_max: float | None = None
        manual_step: float | None = None
        if mode == "manual":
            with st.form(
                key=f"manual_grid_form::{control_scope}",
                enter_to_submit=False,
                border=False,
            ):
                manual_col1, manual_col2, manual_col3 = st.columns(3)
                manual_col1.number_input(
                    tr("Manual min", language),
                    key=manual_min_draft_key,
                )
                manual_col2.number_input(
                    tr("Manual max", language),
                    key=manual_max_draft_key,
                )
                manual_col3.number_input(
                    tr("Manual step", language),
                    key=manual_step_draft_key,
                    min_value=0.01,
                )
                st.caption(tr("Changes take effect after clicking Apply.", language))
                manual_grid_submitted = st.form_submit_button(tr("Apply", language))
            manual_min, manual_max, manual_step = apply_manual_grid_settings(
                submitted=manual_grid_submitted,
                draft_min=float(st.session_state.get(manual_min_draft_key, manual_min_state)),
                draft_max=float(st.session_state.get(manual_max_draft_key, manual_max_state)),
                draft_step=float(st.session_state.get(manual_step_draft_key, 5.0)),
                stored_min=manual_min_state,
                stored_max=manual_max_state,
                stored_step=float(st.session_state.get(manual_step_key, 5.0)),
            )
            st.session_state[manual_min_key] = manual_min
            st.session_state[manual_max_key] = manual_max
            st.session_state[manual_step_key] = manual_step

    unit_cost = float(cost_map.get(unit_cost_key, 0.0)) if economics_enabled else None
    tested_price_benchmarks = (
        [
            PriceBenchmark(
                label=tr("Tested Price", language),
                price=float(tested_price_value),
                key="tested_price",
            )
        ]
        if tested_price_active and tested_price_value is not None
        else []
    )
    selection_key = _selection_key(str(selected_product), str(selected_segment))
    if not tested_price_benchmarks:
        _clear_tested_price_marker_overrides(selection_key)
    tested_price_marker_option = (
        [("tested_price", tr("Tested Price", language))] if tested_price_benchmarks else []
    )
    marker_options_by_chart = {
        "psm": [
            ("pmi", "PMI"),
            ("opp", "OPP"),
            ("idp", "IDP"),
            ("pme", "PME"),
            *tested_price_marker_option,
        ],
        "turnover": [
            ("max_turnover_price", tr("Max Turnover Price", language)),
            *tested_price_marker_option,
        ],
        "nms": [
            ("max_trial", tr("MaxTrial", language)),
            *tested_price_marker_option,
            ("max_revenue", tr("MaxRevenue", language)),
        ],
    }
    psm_marker_overrides = _marker_label_side_overrides(selection_key, "psm")
    turnover_marker_overrides = _marker_label_side_overrides(selection_key, "turnover")
    nms_marker_overrides = _marker_label_side_overrides(selection_key, "nms")

    grid_cfg = _build_grid_config(mode, snap_enabled, manual_min, manual_max, manual_step)

    qc = compute_qc_report(
        group_df,
        puki_threshold=puki_threshold,
        apply_puki_filter=has_puki,
    )
    valid_df, valid_mask = apply_psm_validity_filter(group_df)
    invalid_ordering_n = int((~valid_mask).sum())
    analysis_base_df = valid_df if plausibility_filter_enabled else group_df.copy()
    puki_filtered_df, puki_analysis_mask = apply_puki_filter(
        analysis_base_df,
        puki_threshold=puki_threshold,
        enabled=has_puki,
    )
    puki_filter_applied_to_analysis = has_puki
    puki_excluded_from_analysis_n = int((~puki_analysis_mask).sum()) if has_puki else 0
    outlier_result = apply_outlier_filter(
        puki_filtered_df,
        columns=PRICE_COLUMNS,
        level=outlier_level,
        enabled=outlier_enabled,
    )
    analysis_df = outlier_result.filtered_df

    if plausibility_filter_enabled and len(valid_df) == 0:
        render_notice(tr("No PSM-valid respondents after applying ordering checks.", language))
        st.dataframe(qc.as_frame(), width="stretch")
        render_page_nav_bottom("results")
        return

    if not plausibility_filter_enabled and invalid_ordering_n > 0:
        render_notice(
            tr(
                (
                    "Plausibility filter is disabled: {count} respondents "
                    "with non-ordered thresholds are included."
                ),
                language,
                count=invalid_ordering_n,
            )
        )

    if len(analysis_df) == 0:
        render_notice(
            tr(
                "No respondents remain in the current analysis base after PUKI/outlier filtering.",
                language,
            )
        )
        qc_df = qc.as_frame()
        qc_df["plausibility_filter_applied"] = plausibility_filter_enabled
        qc_df["invalid_ordering_n"] = invalid_ordering_n
        qc_df["excluded_psm_n"] = invalid_ordering_n if plausibility_filter_enabled else 0
        qc_df["included_invalid_ordering_n"] = (
            0 if plausibility_filter_enabled else invalid_ordering_n
        )
        qc_df["outlier_filter_applied"] = outlier_result.enabled
        qc_df["outlier_level"] = outlier_result.level
        qc_df["outlier_q_low"] = outlier_result.q_low
        qc_df["outlier_q_high"] = outlier_result.q_high
        qc_df["outlier_excluded_n"] = outlier_result.excluded_n
        qc_df["puki_filter_applied_to_analysis"] = puki_filter_applied_to_analysis
        qc_df["puki_excluded_from_analysis_n"] = puki_excluded_from_analysis_n
        qc_df["analysis_n_after_outlier"] = 0
        st.dataframe(qc_df, width="stretch")
        render_page_nav_bottom("results")
        return

    try:
        grid_details = build_price_grid_details(analysis_df, grid_cfg, currency=currency)
    except ValueError as exc:
        render_notice(str(exc))
        render_page_nav_bottom("results")
        return

    weight_col = _weight_column(analysis_df)
    _weights, psm_weighting_applied = resolve_psm_weights(analysis_df, weight_col)
    curves = compute_psm_curves(analysis_df, grid_details.prices, weight_col=weight_col)
    kpi_result = compute_psm_kpis(curves)
    kpi_dict = kpi_result.as_dict()
    figure = make_psm_figure(
        curves,
        kpi_result,
        price_benchmarks=tested_price_benchmarks,
        label_side_overrides=psm_marker_overrides,
        language=language,
    )
    tested_price_axis_values = [float(tested_price_value)] if tested_price_benchmarks else []
    _apply_focus_autoscale(
        figure,
        kpis=kpi_dict,
        increment=grid_details.increment,
        extra_prices=tested_price_axis_values,
    )
    _apply_psm_axis_footer(
        figure,
        selected_product=str(selected_product),
        selected_segment=str(selected_segment),
        currency=currency,
        total_n=len(group_df),
        valid_n=len(valid_df),
        analysis_n=len(analysis_df),
        language=language,
    )

    nms_result = None
    if _has_nms_columns(analysis_df):
        nms_result = compute_nms(
            analysis_df,
            grid_details.prices,
            weight_col=weight_col,
            puki_threshold=puki_threshold,
        )

    pi_ladder_df: pd.DataFrame | None = st.session_state.get("psm_pi_ladder_df")
    selected_ladder = _select_pi_ladder_for_group(
        pi_ladder_df,
        segment=str(selected_segment),
        currency=currency,
        product_id=str(selected_product),
    )
    turnover_result = None
    turnover_source: str | None = None
    try:
        pi_curve, turnover_source = resolve_purchase_intention_curve(
            grid_details.prices,
            pi_ladder_df=selected_ladder,
            nms_curves=(nms_result.curves if nms_result is not None else None),
        )
        turnover_result = compute_turnover_index(grid_details.prices, pi_curve)
    except ValueError:
        turnover_result = None
        turnover_source = None

    profit_result = None
    if turnover_result is not None and unit_cost is not None:
        profit_result = compute_profit_proxy(
            grid_details.prices,
            turnover_result.df["purchase_intention_pct"].to_numpy(dtype=float),
            float(unit_cost),
        )

    additional_metrics = compute_additional_metrics(
        kpis=kpi_dict,
        max_turnover_price=(
            float(turnover_result.max_turnover_price) if turnover_result is not None else None
        ),
        unit_cost=(float(unit_cost) if unit_cost is not None else None),
    )

    pi_unit_notes: list[str] = []
    for warning in st.session_state.get("psm_validation_warnings", []):
        warning_text = str(warning)
        has_pi_prefix = warning_text.startswith("PI unit")
        has_tiny_fraction_hint = "fractions but are extremely small" in warning_text
        if has_pi_prefix or has_tiny_fraction_hint:
            pi_unit_notes.append(warning_text)
    if nms_result is not None and nms_result.pi_unit_note:
        pi_unit_notes.append(str(nms_result.pi_unit_note))
    if selected_ladder is not None:
        ladder_note = selected_ladder.attrs.get("pi_unit_note")
        if ladder_note:
            pi_unit_notes.append(str(ladder_note))
    pi_unit_notes = list(dict.fromkeys(pi_unit_notes))

    increment = getattr(grid_details, "increment", None)
    grid_method = getattr(grid_details, "method", "legacy")
    grid_p05 = getattr(grid_details, "p05", None)
    grid_p95 = getattr(grid_details, "p95", None)
    increment_label = "None" if increment is None else f"{increment:g}"
    p05_label = "n/a" if grid_p05 is None else f"{grid_p05:.2f}"
    p95_label = "n/a" if grid_p95 is None else f"{grid_p95:.2f}"

    qc_df = qc.as_frame()
    qc_df["plausibility_filter_applied"] = plausibility_filter_enabled
    qc_df["invalid_ordering_n"] = invalid_ordering_n
    qc_df["excluded_psm_n"] = invalid_ordering_n if plausibility_filter_enabled else 0
    qc_df["included_invalid_ordering_n"] = 0 if plausibility_filter_enabled else invalid_ordering_n
    qc_df["outlier_filter_applied"] = outlier_result.enabled
    qc_df["outlier_level"] = outlier_result.level
    qc_df["outlier_q_low"] = outlier_result.q_low
    qc_df["outlier_q_high"] = outlier_result.q_high
    qc_df["outlier_excluded_n"] = outlier_result.excluded_n
    qc_df["puki_filter_applied_to_analysis"] = puki_filter_applied_to_analysis
    qc_df["puki_excluded_from_analysis_n"] = puki_excluded_from_analysis_n
    qc_df["analysis_n_after_outlier"] = int(len(analysis_df))
    qc_df["psm_weighting_applied"] = psm_weighting_applied

    derived_metric_payload: dict[str, dict[str, float | str | bool | None]] = {}

    has_profit_tab = (
        profit_result is not None and unit_cost is not None and turnover_result is not None
    )
    tab_specs = _build_results_tab_specs(
        has_turnover=turnover_result is not None,
        has_profit=has_profit_tab,
        has_nms=nms_result is not None,
        language=language,
    )
    tab_objects = st.tabs([label for label, _ in tab_specs])
    tab_map = {key: tab for tab, (_, key) in zip(tab_objects, tab_specs, strict=False)}

    with tab_map["psm"]:
        with st.container(border=True):
            st.plotly_chart(figure, width="stretch")
        _render_marker_label_override_controls(
            selection_key=selection_key,
            chart_id="psm",
            marker_options=marker_options_by_chart["psm"],
            language=language,
        )
        _render_selection_controls_box(
            product_values=product_values,
            segment_values=segment_values,
            selected_product=str(selected_product),
            selected_segment=str(selected_segment),
            grid_method=grid_method,
            increment_label=increment_label,
            min_price=grid_details.min_price,
            max_price=grid_details.max_price,
            step=grid_details.step,
            p05_label=p05_label,
            p95_label=p95_label,
            product_key="results_selected_product",
            country_key="results_selected_segment",
            language=language,
        )

        derived_metric_payload = _render_kpi_cards(
            currency + " ",
            kpi_dict,
            additional_metrics,
            language,
        )

        with st.container(border=True):
            st.markdown(f"**{tr('Summary', language)}**")
            summary_lines = build_psm_summary(
                kpi_dict,
                currency=currency,
                segment_label=str(selected_segment),
                product_label=str(selected_product),
                language=language,
            )
            _render_summary_bullets(summary_lines, language)

    if "turnover" in tab_map and turnover_result is not None:
        with tab_map["turnover"]:
            for note in pi_unit_notes:
                st.caption(tr("PI unit note: {note}", language, note=note))
            turnover_fig = make_pi_economics_figure(
                turnover_result,
                currency=currency,
                mode="turnover",
                price_benchmarks=tested_price_benchmarks,
                label_side_overrides=turnover_marker_overrides,
                language=language,
            )
            max_trial_like_price = _series_max_price(turnover_result.df, "purchase_intention_pct")
            _apply_pair_focus_autoscale(
                turnover_fig,
                first_price=float(turnover_result.max_turnover_price),
                second_price=max_trial_like_price,
                increment=increment,
                extra_prices=tested_price_axis_values,
            )
            _apply_psm_axis_footer(
                turnover_fig,
                selected_product=str(selected_product),
                selected_segment=str(selected_segment),
                currency=currency,
                total_n=len(group_df),
                valid_n=len(valid_df),
                analysis_n=len(analysis_df),
                language=language,
            )
            with st.container(border=True):
                st.plotly_chart(turnover_fig, width="stretch")
            _render_marker_label_override_controls(
                selection_key=selection_key,
                chart_id="turnover",
                marker_options=marker_options_by_chart["turnover"],
                language=language,
            )
            _render_selection_controls_box(
                product_values=product_values,
                segment_values=segment_values,
                selected_product=str(selected_product),
                selected_segment=str(selected_segment),
                grid_method=grid_method,
                increment_label=increment_label,
                min_price=grid_details.min_price,
                max_price=grid_details.max_price,
                step=grid_details.step,
                p05_label=p05_label,
                p95_label=p95_label,
                product_key="results_selected_product_turnover",
                country_key="results_selected_segment_turnover",
                language=language,
            )
            source_label, source_note = describe_turnover_source(turnover_source, language)
            turnover_recommendation_allowed = can_recommend(
                {"opp": str(kpi_dict.get("opp_status", "closest"))},
                allow_interval=False,
            )
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1:
                max_turnover_display = (
                    f"{currency} {turnover_result.max_turnover_price:.2f}"
                    if turnover_recommendation_allowed
                    else "—"
                )
                _render_kpi_card(
                    title=tr("Maximum Turnover Price", language),
                    subtitle=_subtitle_with_badges(
                        tr("Price where turnover index reaches its maximum", language),
                        lens=tr("Economics proxy", language),
                        caution=None if turnover_recommendation_allowed else "unstable",
                        language=language,
                    ),
                    value=max_turnover_display,
                )
            with t_col2:
                max_turnover_index_display = (
                    f"{turnover_result.max_turnover_index:.2f}"
                    if turnover_recommendation_allowed
                    else "—"
                )
                _render_kpi_card(
                    title=tr("Maximum Turnover Index", language),
                    subtitle=_subtitle_with_badges(
                        tr("Normalized turnover score at max-turnover price", language),
                        lens=tr("Economics proxy", language),
                        caution=None if turnover_recommendation_allowed else "unstable",
                        language=language,
                    ),
                    value=max_turnover_index_display,
                )
            with t_col3:
                _render_kpi_card(
                    title=tr("PI Source", language),
                    subtitle=_subtitle_with_badges(
                        source_note,
                        lens=tr("Modeled demand", language),
                        language=language,
                    ),
                    value=source_label,
                )
            st.markdown("<div class='psm-kpi-row-gap'></div>", unsafe_allow_html=True)
            derived_metric_payload["max_turnover_price"] = {
                "is_stable": turnover_recommendation_allowed,
                "display_value": max_turnover_display,
                "diagnostic_value": float(turnover_result.max_turnover_price),
                "reason": (
                    None
                    if turnover_recommendation_allowed
                    else tr("Requires clean OPP for optimization statements.", language)
                ),
                "lens": tr("Economics proxy", language),
            }
            derived_metric_payload["max_turnover_index"] = {
                "is_stable": turnover_recommendation_allowed,
                "display_value": max_turnover_index_display,
                "diagnostic_value": float(turnover_result.max_turnover_index),
                "reason": (
                    None
                    if turnover_recommendation_allowed
                    else tr("Requires clean OPP for optimization statements.", language)
                ),
                "lens": tr("Economics proxy", language),
            }

            with st.container(border=True):
                st.markdown(f"**{tr('Purchase Intention and Turnover Summary', language)}**")
                summary_lines = _build_turnover_summary_safe(
                    turnover_result=turnover_result,
                    currency=currency,
                    segment_label=str(selected_segment),
                    source=turnover_source,
                    kpi_statuses={
                        "opp": str(kpi_dict.get("opp_status", "closest")),
                    },
                    language=language,
                )
                _render_summary_bullets(summary_lines, language)

    if "profit" in tab_map and turnover_result is not None and profit_result is not None:
        with tab_map["profit"]:
            for note in pi_unit_notes:
                st.caption(tr("PI unit note: {note}", language, note=note))
            profit_fig = make_pi_economics_figure(
                turnover_result,
                currency=currency,
                mode="profit",
                profit_result=profit_result,
                unit_cost=float(unit_cost),
                price_benchmarks=tested_price_benchmarks,
                language=language,
            )
            _apply_pair_focus_autoscale(
                profit_fig,
                first_price=float(profit_result.max_profit_price),
                second_price=float(turnover_result.max_turnover_price),
                increment=increment,
                extra_prices=tested_price_axis_values,
            )
            _apply_psm_axis_footer(
                profit_fig,
                selected_product=str(selected_product),
                selected_segment=str(selected_segment),
                currency=currency,
                total_n=len(group_df),
                valid_n=len(valid_df),
                analysis_n=len(analysis_df),
                language=language,
            )
            with st.container(border=True):
                st.plotly_chart(profit_fig, width="stretch")
            _render_selection_controls_box(
                product_values=product_values,
                segment_values=segment_values,
                selected_product=str(selected_product),
                selected_segment=str(selected_segment),
                grid_method=grid_method,
                increment_label=increment_label,
                min_price=grid_details.min_price,
                max_price=grid_details.max_price,
                step=grid_details.step,
                p05_label=p05_label,
                p95_label=p95_label,
                product_key="results_selected_product_profit",
                country_key="results_selected_segment_profit",
                language=language,
            )
            profit_recommendation_allowed = can_recommend(
                {
                    "pmi": str(kpi_dict.get("pmi_status", "closest")),
                    "pme": str(kpi_dict.get("pme_status", "closest")),
                },
                allow_interval=False,
            )
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                max_profit_display = (
                    f"{currency} {profit_result.max_profit_price:.2f}"
                    if profit_recommendation_allowed
                    else "—"
                )
                _render_kpi_card(
                    title=tr("Maximum Profit Price", language),
                    subtitle=_subtitle_with_badges(
                        tr("Price where profit proxy reaches its maximum", language),
                        lens=tr("Economics proxy", language),
                        caution=None if profit_recommendation_allowed else "unstable",
                        language=language,
                    ),
                    value=max_profit_display,
                )
            with p_col2:
                _render_kpi_card(
                    title=tr("Break-even (Cost)", language),
                    subtitle=_subtitle_with_badges(
                        tr("Price where unit margin equals zero", language),
                        lens=tr("Economics proxy", language),
                        language=language,
                    ),
                    value=f"{currency} {float(unit_cost):.2f}",
                )
            with p_col3:
                max_profit_index_display = (
                    f"{profit_result.max_profit_index:.2f}"
                    if profit_recommendation_allowed
                    else "—"
                )
                _render_kpi_card(
                    title=tr("Maximum Profit Index", language),
                    subtitle=_subtitle_with_badges(
                        tr("Normalized profit proxy score at the optimum", language),
                        lens=tr("Economics proxy", language),
                        caution=None if profit_recommendation_allowed else "unstable",
                        language=language,
                    ),
                    value=max_profit_index_display,
                )
            st.markdown("<div class='psm-kpi-row-gap'></div>", unsafe_allow_html=True)
            derived_metric_payload["max_profit_price"] = {
                "is_stable": profit_recommendation_allowed,
                "display_value": max_profit_display,
                "diagnostic_value": float(profit_result.max_profit_price),
                "reason": (
                    None
                    if profit_recommendation_allowed
                    else tr("Requires clean PMI and PME for optimization statements.", language)
                ),
                "lens": tr("Economics proxy", language),
            }
            derived_metric_payload["max_profit_index"] = {
                "is_stable": profit_recommendation_allowed,
                "display_value": max_profit_index_display,
                "diagnostic_value": float(profit_result.max_profit_index),
                "reason": (
                    None
                    if profit_recommendation_allowed
                    else tr("Requires clean PMI and PME for optimization statements.", language)
                ),
                "lens": tr("Economics proxy", language),
            }
            with st.container(border=True):
                st.markdown(f"**{tr('Profit Summary', language)}**")
                summary_lines = _build_profit_summary_safe(
                    profit_result=profit_result,
                    currency=currency,
                    segment_label=str(selected_segment),
                    product_label=str(selected_product),
                    kpi_statuses={
                        "pmi": str(kpi_dict.get("pmi_status", "closest")),
                        "pme": str(kpi_dict.get("pme_status", "closest")),
                    },
                    language=language,
                )
                _render_summary_bullets(summary_lines, language)

    if "nms_trial_revenue" in tab_map and nms_result is not None:
        with tab_map["nms_trial_revenue"]:
            for note in pi_unit_notes:
                st.caption(tr("PI unit note: {note}", language, note=note))
            nms_fig = make_nms_figure(
                nms_result,
                price_benchmarks=tested_price_benchmarks,
                label_side_overrides=nms_marker_overrides,
                language=language,
            )
            _apply_pair_focus_autoscale(
                nms_fig,
                first_price=float(nms_result.max_trial_price),
                second_price=float(nms_result.max_revenue_price),
                increment=increment,
                extra_prices=tested_price_axis_values,
            )
            _apply_psm_axis_footer(
                nms_fig,
                selected_product=str(selected_product),
                selected_segment=str(selected_segment),
                currency=currency,
                total_n=len(group_df),
                valid_n=len(valid_df),
                analysis_n=int(nms_result.included_n),
                language=language,
            )
            with st.container(border=True):
                st.plotly_chart(nms_fig, width="stretch")
            _render_marker_label_override_controls(
                selection_key=selection_key,
                chart_id="nms",
                marker_options=marker_options_by_chart["nms"],
                language=language,
            )
            _render_selection_controls_box(
                product_values=product_values,
                segment_values=segment_values,
                selected_product=str(selected_product),
                selected_segment=str(selected_segment),
                grid_method=grid_method,
                increment_label=increment_label,
                min_price=grid_details.min_price,
                max_price=grid_details.max_price,
                step=grid_details.step,
                p05_label=p05_label,
                p95_label=p95_label,
                product_key="results_selected_product_nms",
                country_key="results_selected_segment_nms",
                language=language,
            )
            n_col1, n_col2, n_col3 = st.columns(3)
            with n_col1:
                _render_kpi_card(
                    title=tr("Max Trial Price", language),
                    subtitle=tr("(Price where modeled trial intent reaches its maximum)", language),
                    value=f"{currency} {nms_result.max_trial_price:.2f}",
                )
            with n_col2:
                _render_kpi_card(
                    title=tr("Max Revenue Price", language),
                    subtitle=tr(
                        "(Price where modeled revenue per 100 reaches its maximum)", language
                    ),
                    value=f"{currency} {nms_result.max_revenue_price:.2f}",
                )
            with n_col3:
                _render_kpi_card(
                    title=tr("NMS Included N", language),
                    subtitle=tr(
                        "(Respondents included after PI eligibility and missing checks)", language
                    ),
                    value=str(nms_result.included_n),
                )
            st.markdown("<div class='psm-kpi-row-gap'></div>", unsafe_allow_html=True)
            if nms_result.filter_note:
                st.caption(tr(str(nms_result.filter_note), language))
            if weight_col and not nms_result.weighting_applied:
                st.caption(
                    tr(
                        (
                            "NMS weight fallback active: invalid/empty weights "
                            "were replaced by unweighted averaging."
                        ),
                        language,
                    )
                )
            with st.container(border=True):
                st.markdown(f"**{tr('Summary', language)}**")
                summary_lines = build_nms_summary(
                    nms_result,
                    currency=currency,
                    segment_label=str(selected_segment),
                    language=language,
                )
                _render_summary_bullets(summary_lines, language)

    with tab_map["kpi_summary"]:
        kpi_summary_fig = make_kpi_summary_figure(
            {
                "product_id": selected_product,
                "segment": selected_segment,
                "currency": currency,
                "kpis": kpi_dict,
                "turnover_index_result": turnover_result,
                "tested_price": tested_price_value,
                "tested_price_active": bool(tested_price_active),
                "language": language,
            }
        )
        with st.container(border=True):
            st.plotly_chart(kpi_summary_fig, width="stretch")

    with tab_map["quality_control"]:
        st.dataframe(qc_df, width="stretch")
        if weight_col and not psm_weighting_applied:
            st.caption(
                tr(
                    (
                        "Weight fallback active: weight column exists but is "
                        "unusable (all missing/zero/invalid). Unweighted "
                        "calculation was applied."
                    ),
                    language,
                )
            )
        with st.expander(tr("Outlier bounds", language), expanded=False):
            st.dataframe(outlier_result.bounds.reset_index(), width="stretch")

    st.session_state["psm_analysis_payload"] = {
        "product_id": selected_product,
        "segment": selected_segment,
        "currency": currency,
        "group_df": group_df,
        "valid_df": valid_df,
        "analysis_df": analysis_df,
        "curves": curves,
        "kpis": kpi_dict,
        "kpi_result": kpi_result,
        "nms_result": nms_result,
        "turnover_index_result": turnover_result,
        "profit_proxy_result": profit_result,
        "additional_metrics": {key: metric.as_dict() for key, metric in additional_metrics.items()},
        "derived_metric_status": derived_metric_payload,
        "turnover_source": turnover_source,
        "unit_cost": unit_cost,
        "tested_price": tested_price_value,
        "tested_price_active": bool(tested_price_active),
        "language": language,
        "marker_label_side_overrides": dict(
            st.session_state.get("marker_label_side_overrides_by_key", {}).get(selection_key, {})
        ),
        "puki_threshold": puki_threshold,
        "puki_filter_applied_to_analysis": puki_filter_applied_to_analysis,
        "puki_excluded_from_analysis_n": puki_excluded_from_analysis_n,
        "plausibility_filter_applied": plausibility_filter_enabled,
        "invalid_ordering_n": invalid_ordering_n,
        "outlier_settings": {
            "enabled": outlier_result.enabled,
            "level": outlier_result.level,
            "q_low": outlier_result.q_low,
            "q_high": outlier_result.q_high,
        },
        "outlier_stats": {
            "excluded_n": outlier_result.excluded_n,
            "analysis_n_after_outlier": int(len(analysis_df)),
        },
        "outlier_bounds": outlier_result.bounds.reset_index(),
        "psm_weighting_applied": psm_weighting_applied,
        "grid": {
            "min_price": grid_details.min_price,
            "max_price": grid_details.max_price,
            "step": grid_details.step,
            "increment": increment,
            "snapped": bool(getattr(grid_details, "snapped", increment is not None)),
            "p05": grid_p05,
            "p95": grid_p95,
            "method": grid_method,
        },
        "qc": qc_df,
    }

    render_page_nav_bottom("results")


if __name__ == "__main__":
    main()
