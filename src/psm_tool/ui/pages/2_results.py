from __future__ import annotations

import pandas as pd
import streamlit as st

from psm_tool.config import GridConfig
from psm_tool.core.curves import compute_psm_curves, resolve_psm_weights
from psm_tool.core.grid import build_price_grid_details
from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.nms import compute_nms
from psm_tool.core.outliers import apply_outlier_filter
from psm_tool.core.qc import apply_psm_validity_filter, compute_qc_report
from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.psm_plot import make_psm_figure
from psm_tool.report.insights import build_kpi_explanations, build_psm_summary

PRICE_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]
OUTLIER_LABEL_TO_LEVEL = {"Mild": "mild", "Medium": "medium", "Streng": "strict"}


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


def _render_kpi_cards(price_symbol: str, kpis: dict[str, float | str]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("PMI", f"{price_symbol}{kpis['pmi']:.2f}")
    col2.metric("OPP", f"{price_symbol}{kpis['opp']:.2f}")
    col3.metric("IDP", f"{price_symbol}{kpis['idp']:.2f}")
    col4.metric("PME", f"{price_symbol}{kpis['pme']:.2f}")

    col5, col6 = st.columns(2)
    col5.metric(
        "Accepted Range",
        f"{price_symbol}{kpis['accepted_low']:.2f} - {price_symbol}{kpis['accepted_high']:.2f}",
    )
    col6.metric(
        "Price Stress (OPP - IDP)",
        f"{kpis['price_stress']:.2f} ({kpis['stress_flag']})",
    )


def main() -> None:
    st.title("2. Results")
    df: pd.DataFrame | None = st.session_state.get("psm_input_df")
    if df is None:
        st.warning("No dataset loaded. Open page '1 Upload' first.")
        return

    product_values = sorted(_series_or_default(df, "product_id", "default_product").unique())
    selected_product = st.selectbox("Product", options=product_values, index=0)

    product_df = df.loc[
        _series_or_default(df, "product_id", "default_product") == selected_product
    ].copy()
    segment_values = sorted(_series_or_default(product_df, "segment", "default_segment").unique())
    selected_segment = st.selectbox("Segment", options=segment_values, index=0)

    group_df = product_df.loc[
        _series_or_default(product_df, "segment", "default_segment") == selected_segment
    ].copy()
    if len(group_df) == 0:
        st.warning("No data for selected product/segment.")
        return

    st.subheader("Price Grid Settings")
    cfg_col1, cfg_col2 = st.columns(2)
    mode = cfg_col1.selectbox("Grid mode", options=["auto", "manual"], index=0)
    snap_enabled = cfg_col2.toggle("Snap to currency increment", value=True)

    manual_min: float | None = None
    manual_max: float | None = None
    manual_step: float | None = None
    if mode == "manual":
        manual_col1, manual_col2, manual_col3 = st.columns(3)
        manual_min = float(manual_col1.number_input("Manual min", value=0.0))
        manual_max = float(manual_col2.number_input("Manual max", value=100.0))
        manual_step = float(manual_col3.number_input("Manual step", value=5.0, min_value=0.01))

    st.subheader("Data Guardrails")
    outlier_col1, outlier_col2 = st.columns(2)
    outlier_enabled = outlier_col1.toggle("Ausreißerfilter aktiv", value=False)
    outlier_label = "Medium"
    if outlier_enabled:
        outlier_label = outlier_col2.selectbox(
            "Ausreißer-Härte",
            options=["Mild", "Medium", "Streng"],
            index=1,
        )
    outlier_level = OUTLIER_LABEL_TO_LEVEL[outlier_label]

    currency = str(_series_or_default(group_df, "currency", "").iloc[0]).upper()
    grid_cfg = _build_grid_config(mode, snap_enabled, manual_min, manual_max, manual_step)
    has_puki = "puki" in group_df.columns
    puki_threshold = 2
    if has_puki:
        include_neutral = st.toggle("Include neutral PUKI (<=3)", value=False, key="puki_neutral")
        puki_threshold = 3 if include_neutral else 2
    else:
        st.caption("PUKI column missing: PI filter is not applied.")

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
    figure = make_psm_figure(curves, kpi_result)

    increment = getattr(grid_details, "increment", None)
    grid_method = getattr(grid_details, "method", "legacy")
    grid_p05 = getattr(grid_details, "p05", None)
    grid_p95 = getattr(grid_details, "p95", None)
    increment_label = "None" if increment is None else f"{increment:g}"
    p05_label = "n/a" if grid_p05 is None else f"{grid_p05:.2f}"
    p95_label = "n/a" if grid_p95 is None else f"{grid_p95:.2f}"
    st.caption(
        f"Grid method={grid_method} | "
        f"Grid increment used: {increment_label} | "
        f"grid_min={grid_details.min_price:.2f} | "
        f"grid_max={grid_details.max_price:.2f} | "
        f"grid_step={grid_details.step:.2f} | "
        f"p05={p05_label} | p95={p95_label}"
    )
    st.plotly_chart(figure, use_container_width=True)

    kpi_dict = kpi_result.as_dict()
    _render_kpi_cards(currency + " ", kpi_dict)

    nms_result = None
    if _has_nms_columns(analysis_df):
        nms_result = compute_nms(
            analysis_df,
            grid_details.prices,
            weight_col=weight_col,
            puki_threshold=puki_threshold,
        )

    st.subheader("Key Facts")
    key_facts = pd.DataFrame(build_kpi_explanations(kpi_dict))
    st.dataframe(key_facts, use_container_width=True, hide_index=True)

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
    st.subheader("Summary")
    for sentence in summary_lines:
        st.markdown(f"- {sentence}")

    st.subheader("Quality Control")
    qc_df = qc.as_frame()
    qc_df["excluded_psm_n"] = int((~valid_mask).sum())
    qc_df["outlier_filter_applied"] = outlier_result.enabled
    qc_df["outlier_level"] = outlier_result.level
    qc_df["outlier_q_low"] = outlier_result.q_low
    qc_df["outlier_q_high"] = outlier_result.q_high
    qc_df["outlier_excluded_n"] = outlier_result.excluded_n
    qc_df["analysis_n_after_outlier"] = int(len(analysis_df))
    qc_df["psm_weighting_applied"] = psm_weighting_applied
    st.dataframe(qc_df, use_container_width=True)
    if weight_col and not psm_weighting_applied:
        st.caption(
            "Weight fallback active: weight column exists but is unusable "
            "(all missing/zero/invalid). Unweighted calculation was applied."
        )

    if nms_result is not None:
        st.subheader("NMS Trial + Revenue")
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
    else:
        st.info("PI columns are missing. NMS chart is not available for this selection.")

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
