from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from psm_tool.config import GridConfig
from psm_tool.core.curves import compute_psm_curves, resolve_psm_weights
from psm_tool.core.grid import build_price_grid_details
from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.nms import compute_nms
from psm_tool.core.outliers import apply_outlier_filter
from psm_tool.core.qc import apply_psm_validity_filter, compute_qc_report
from psm_tool.core.turnover_index import (
    compute_profit_proxy,
    compute_turnover_index,
    resolve_purchase_intention_curve,
)
from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.psm_plot import make_psm_figure
from psm_tool.plots.turnover_index_plot import make_pi_economics_figure
from psm_tool.report.insights import (
    build_kpi_explanations,
    build_nms_explanations,
    build_nms_summary,
    build_profit_explanations,
    build_profit_summary,
    build_psm_summary,
    build_turnover_explanations,
    build_turnover_summary,
)
from psm_tool.ui.style import inject_base_styles

PRICE_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]
OUTLIER_LABEL_TO_LEVEL = {"Mild": "mild", "Medium": "medium", "Strict": "strict"}


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


def _on_unit_cost_change(target_key: str, widget_key: str) -> None:
    mapping = st.session_state.setdefault("unit_cost_by_product", {})
    mapping[target_key] = float(st.session_state[widget_key])


def _render_kpi_cards(price_symbol: str, kpis: dict[str, float | str]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "PMI (Point of Marginal Inexpensiveness)",
        f"{price_symbol}{kpis['pmi']:.2f}",
    )
    col2.metric("OPP (Optimal Pricing Point)", f"{price_symbol}{kpis['opp']:.2f}")
    col3.metric("IDP (Indifference Pricing Point)", f"{price_symbol}{kpis['idp']:.2f}")
    col4.metric("PME (Point of Marginal Expensiveness)", f"{price_symbol}{kpis['pme']:.2f}")

    col5, col6 = st.columns(2)
    col5.metric(
        "Accepted Range",
        f"{price_symbol}{kpis['accepted_low']:.2f} - {price_symbol}{kpis['accepted_high']:.2f}",
    )
    col6.metric(
        "Price Stress (OPP - IDP)",
        f"{kpis['price_stress']:.2f} ({kpis['stress_flag']})",
    )


def _render_context_banner(
    *,
    selected_product: str,
    selected_segment: str,
    currency: str,
    total_n: int,
    valid_n: int,
    analysis_n: int,
) -> None:
    with st.container(border=True):
        selection_text = f"{escape(selected_product)} / {escape(selected_segment)}"
        currency_text = escape(currency or "n/a")
        analysis_text = f"{analysis_n} (valid {valid_n} / total {total_n})"
        st.markdown(
            (
                "<div class='psm-context-grid'>"
                "<div class='psm-context-chip'>"
                "<span class='label'>Selection</span>"
                f"<span class='value'>{selection_text}</span>"
                "</div>"
                "<div class='psm-context-chip'>"
                "<span class='label'>Currency</span>"
                f"<span class='value'>{currency_text}</span>"
                "</div>"
                "<div class='psm-context-chip'>"
                "<span class='label'>Analysis N</span>"
                f"<span class='value'>{analysis_text}</span>"
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def main() -> None:
    inject_base_styles(max_width=1820)
    st.markdown('<p class="psm-page-eyebrow">Analysis Workspace</p>', unsafe_allow_html=True)
    st.title("2. Results")

    df: pd.DataFrame | None = st.session_state.get("psm_input_df")
    if df is None:
        st.warning("No dataset loaded. Open page '1 Upload' first.")
        return

    with st.container(border=True):
        st.subheader("Selection")
        select_col1, select_col2 = st.columns(2)
        product_values = sorted(_series_or_default(df, "product_id", "default_product").unique())
        selected_product = select_col1.selectbox("Product", options=product_values, index=0)

        product_df = df.loc[
            _series_or_default(df, "product_id", "default_product") == selected_product
        ].copy()
        segment_values = sorted(
            _series_or_default(product_df, "segment", "default_segment").unique()
        )
        selected_segment = select_col2.selectbox("Segment", options=segment_values, index=0)

    group_df = product_df.loc[
        _series_or_default(product_df, "segment", "default_segment") == selected_segment
    ].copy()
    if len(group_df) == 0:
        st.warning("No data for selected product/segment.")
        return

    with st.container(border=True):
        st.subheader("Analysis Controls")
        mode = st.selectbox("Grid mode", options=["auto", "manual"], index=0)
        snap_enabled = st.toggle("Snap to currency increment", value=True)

        manual_min: float | None = None
        manual_max: float | None = None
        manual_step: float | None = None
        if mode == "manual":
            manual_col1, manual_col2, manual_col3 = st.columns(3)
            manual_min = float(manual_col1.number_input("Manual min", value=0.0))
            manual_max = float(manual_col2.number_input("Manual max", value=100.0))
            manual_step = float(manual_col3.number_input("Manual step", value=5.0, min_value=0.01))

        outlier_col1, outlier_col2 = st.columns(2)
        outlier_enabled = outlier_col1.toggle("Outlier filter enabled", value=False)
        outlier_label = "Medium"
        if outlier_enabled:
            outlier_label = outlier_col2.selectbox(
                "Outlier level",
                options=["Mild", "Medium", "Strict"],
                index=1,
            )
        outlier_level = OUTLIER_LABEL_TO_LEVEL[outlier_label]

        has_puki = "puki" in group_df.columns
        puki_threshold = 2
        if has_puki:
            include_neutral = st.toggle(
                "Include neutral PUKI (<=3)", value=False, key="puki_neutral"
            )
            puki_threshold = 3 if include_neutral else 2
        else:
            st.caption("PUKI column missing: PI filter is not applied.")

        cost_map: dict[str, float] = st.session_state.setdefault("unit_cost_by_product", {})
        unit_cost_key = _cost_key(str(selected_product), str(selected_segment))
        widget_key = f"unit_cost_input::{unit_cost_key}"
        default_cost = float(cost_map.get(unit_cost_key, 0.0))
        with st.expander("Economics (optional)", expanded=False):
            st.caption("Used only for calculations and exports in this session.")
            st.number_input(
                "Unit cost",
                min_value=0.0,
                value=default_cost,
                step=1.0,
                format="%.2f",
                key=widget_key,
                help="Used only for calculations and exports in this session.",
                on_change=_on_unit_cost_change,
                args=(unit_cost_key, widget_key),
            )

    unit_cost = cost_map.get(unit_cost_key)

    currency = str(_series_or_default(group_df, "currency", "").iloc[0]).upper()
    grid_cfg = _build_grid_config(mode, snap_enabled, manual_min, manual_max, manual_step)

    qc = compute_qc_report(
        group_df,
        puki_threshold=puki_threshold,
        apply_puki_filter=has_puki,
    )
    valid_df, valid_mask = apply_psm_validity_filter(group_df)
    outlier_result = apply_outlier_filter(
        valid_df,
        columns=PRICE_COLUMNS,
        level=outlier_level,
        enabled=outlier_enabled,
    )
    analysis_df = outlier_result.filtered_df

    if len(valid_df) == 0:
        st.error("No PSM-valid respondents after applying ordering checks.")
        st.dataframe(qc.as_frame(), use_container_width=True)
        return

    if len(analysis_df) == 0:
        st.error("All PSM-valid respondents were excluded by outlier filtering.")
        qc_df = qc.as_frame()
        qc_df["excluded_psm_n"] = int((~valid_mask).sum())
        qc_df["outlier_filter_applied"] = outlier_result.enabled
        qc_df["outlier_level"] = outlier_result.level
        qc_df["outlier_q_low"] = outlier_result.q_low
        qc_df["outlier_q_high"] = outlier_result.q_high
        qc_df["outlier_excluded_n"] = outlier_result.excluded_n
        qc_df["analysis_n_after_outlier"] = 0
        st.dataframe(qc_df, use_container_width=True)
        return

    try:
        grid_details = build_price_grid_details(analysis_df, grid_cfg, currency=currency)
    except ValueError as exc:
        st.error(str(exc))
        return

    weight_col = _weight_column(analysis_df)
    _weights, psm_weighting_applied = resolve_psm_weights(analysis_df, weight_col)
    curves = compute_psm_curves(analysis_df, grid_details.prices, weight_col=weight_col)
    kpi_result = compute_psm_kpis(curves)
    kpi_dict = kpi_result.as_dict()
    figure = make_psm_figure(curves, kpi_result)

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

    _render_context_banner(
        selected_product=str(selected_product),
        selected_segment=str(selected_segment),
        currency=currency,
        total_n=len(group_df),
        valid_n=len(valid_df),
        analysis_n=len(analysis_df),
    )

    increment = getattr(grid_details, "increment", None)
    grid_method = getattr(grid_details, "method", "legacy")
    grid_p05 = getattr(grid_details, "p05", None)
    grid_p95 = getattr(grid_details, "p95", None)
    increment_label = "None" if increment is None else f"{increment:g}"
    p05_label = "n/a" if grid_p05 is None else f"{grid_p05:.2f}"
    p95_label = "n/a" if grid_p95 is None else f"{grid_p95:.2f}"

    qc_df = qc.as_frame()
    qc_df["excluded_psm_n"] = int((~valid_mask).sum())
    qc_df["outlier_filter_applied"] = outlier_result.enabled
    qc_df["outlier_level"] = outlier_result.level
    qc_df["outlier_q_low"] = outlier_result.q_low
    qc_df["outlier_q_high"] = outlier_result.q_high
    qc_df["outlier_excluded_n"] = outlier_result.excluded_n
    qc_df["analysis_n_after_outlier"] = int(len(analysis_df))
    qc_df["psm_weighting_applied"] = psm_weighting_applied

    psm_tab, nms_tab, qc_tab = st.tabs(["PSM", "NMS Trial + Revenue", "Quality Control"])

    with psm_tab:
        with st.container(border=True):
            st.caption(
                f"Grid method={grid_method} | "
                f"Grid increment used: {increment_label} | "
                f"grid_min={grid_details.min_price:.2f} | "
                f"grid_max={grid_details.max_price:.2f} | "
                f"grid_step={grid_details.step:.2f} | "
                f"p05={p05_label} | p95={p95_label}"
            )
            st.plotly_chart(figure, use_container_width=True)

        _render_kpi_cards(currency + " ", kpi_dict)

        psm_col1, psm_col2 = st.columns([1.1, 1.0])
        with psm_col1:
            st.markdown("**Key Facts**")
            key_facts = pd.DataFrame(build_kpi_explanations(kpi_dict))
            st.dataframe(key_facts, use_container_width=True, hide_index=True)
        with psm_col2:
            st.markdown("**Summary**")
            nms_kpis = None
            if nms_result is not None:
                nms_kpis = {
                    "max_trial_price": nms_result.max_trial_price,
                    "max_revenue_price": nms_result.max_revenue_price,
                }
            summary_lines = build_psm_summary(
                kpi_dict,
                currency=currency,
                segment_label=str(selected_segment),
                nms_kpis=nms_kpis,
            )
            for sentence in summary_lines:
                st.markdown(f"- {sentence}")

    with nms_tab:
        if turnover_result is None and nms_result is None:
            st.info("No purchase intention source available for this selection.")
        else:
            for note in pi_unit_notes:
                st.caption(f"PI unit note: {note}")
            view_options = ["Purchase Intention + Turnover Index (0-100)"]
            if unit_cost is not None and profit_result is not None:
                view_options.append("Profit Index (0-100)")
            if nms_result is not None:
                view_options.append("Trial + Revenue (two axes)")
            view_mode = st.radio("Show", options=view_options, horizontal=True, index=0)

            if view_mode == "Purchase Intention + Turnover Index (0-100)":
                if turnover_result is None:
                    st.info("Unable to compute Turnover Index for this selection.")
                else:
                    with st.container(border=True):
                        st.plotly_chart(
                            make_pi_economics_figure(
                                turnover_result,
                                currency=currency,
                                mode="turnover",
                            ),
                            use_container_width=True,
                        )
                    col_t1, col_t2, col_t3 = st.columns(3)
                    col_t1.metric(
                        "Maximum Turnover Price",
                        f"{currency} {turnover_result.max_turnover_price:.2f}",
                    )
                    col_t2.metric(
                        "Maximum Turnover Index",
                        f"{turnover_result.max_turnover_index:.2f}",
                    )
                    source_label = (
                        "PI ladder" if turnover_source == "ladder" else "NMS trial fallback"
                    )
                    col_t3.metric("PI Source", source_label)
                    turnover_col1, turnover_col2 = st.columns([1.1, 1.0])
                    with turnover_col1:
                        st.markdown("**Turnover Key Facts**")
                        turnover_key_facts = pd.DataFrame(
                            build_turnover_explanations(
                                turnover_result,
                                currency=currency,
                                source=turnover_source,
                            )
                        )
                        st.dataframe(turnover_key_facts, use_container_width=True, hide_index=True)
                    with turnover_col2:
                        st.markdown("**Turnover Summary**")
                        for sentence in build_turnover_summary(
                            turnover_result,
                            currency=currency,
                            segment_label=str(selected_segment),
                            source=turnover_source,
                        ):
                            st.markdown(f"- {sentence}")
            elif view_mode == "Profit Index (0-100)":
                with st.container(border=True):
                    st.plotly_chart(
                        make_pi_economics_figure(
                            turnover_result,
                            currency=currency,
                            mode="profit",
                            profit_result=profit_result,
                            unit_cost=float(unit_cost),
                        ),
                        use_container_width=True,
                    )
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric(
                    "Max Profit Price", f"{currency} {profit_result.max_profit_price:.2f}"
                )
                col_p2.metric("Break-even (Cost)", f"{currency} {float(unit_cost):.2f}")
                col_p3.metric("Max Profit Index", f"{profit_result.max_profit_index:.2f}")
                profit_col1, profit_col2 = st.columns([1.1, 1.0])
                with profit_col1:
                    st.markdown("**Profit Key Facts**")
                    profit_key_facts = pd.DataFrame(
                        build_profit_explanations(profit_result, currency=currency)
                    )
                    st.dataframe(profit_key_facts, use_container_width=True, hide_index=True)
                with profit_col2:
                    st.markdown("**Profit Summary**")
                    for sentence in build_profit_summary(
                        profit_result,
                        currency=currency,
                        segment_label=str(selected_segment),
                    ):
                        st.markdown(f"- {sentence}")
            else:
                with st.container(border=True):
                    st.plotly_chart(make_nms_figure(nms_result), use_container_width=True)
                col_n1, col_n2, col_n3 = st.columns(3)
                col_n1.metric("MaxTrial Price", f"{currency} {nms_result.max_trial_price:.2f}")
                col_n2.metric("MaxRevenue Price", f"{currency} {nms_result.max_revenue_price:.2f}")
                col_n3.metric("NMS Included N", str(nms_result.included_n))
                if nms_result.filter_note:
                    st.caption(nms_result.filter_note)
                if weight_col and not nms_result.weighting_applied:
                    st.caption(
                        "NMS weight fallback active: invalid/empty weights were replaced by "
                        "unweighted averaging."
                    )
                nms_col1, nms_col2 = st.columns([1.1, 1.0])
                with nms_col1:
                    st.markdown("**NMS Key Facts**")
                    nms_key_facts = pd.DataFrame(
                        build_nms_explanations(nms_result, currency=currency)
                    )
                    st.dataframe(nms_key_facts, use_container_width=True, hide_index=True)
                with nms_col2:
                    st.markdown("**NMS Summary**")
                    for sentence in build_nms_summary(
                        nms_result,
                        currency=currency,
                        segment_label=str(selected_segment),
                    ):
                        st.markdown(f"- {sentence}")

    with qc_tab:
        st.dataframe(qc_df, use_container_width=True)
        if weight_col and not psm_weighting_applied:
            st.caption(
                "Weight fallback active: weight column exists but is unusable "
                "(all missing/zero/invalid). Unweighted calculation was applied."
            )
        with st.expander("Outlier bounds", expanded=False):
            st.dataframe(outlier_result.bounds.reset_index(), use_container_width=True)

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
        "turnover_source": turnover_source,
        "unit_cost": unit_cost,
        "puki_threshold": puki_threshold,
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


if __name__ == "__main__":
    main()
