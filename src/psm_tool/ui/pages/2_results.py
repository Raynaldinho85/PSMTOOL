from __future__ import annotations

import pandas as pd
import streamlit as st

from psm_tool.config import GridConfig
from psm_tool.core.curves import compute_psm_curves
from psm_tool.core.grid import build_price_grid_details
from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.nms import compute_nms
from psm_tool.core.qc import apply_psm_validity_filter, compute_qc_report
from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.psm_plot import make_psm_figure


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

    if len(valid_df) == 0:
        st.error("No PSM-valid respondents after applying ordering checks.")
        st.dataframe(qc.as_frame(), use_container_width=True)
        return

    try:
        grid_details = build_price_grid_details(valid_df, grid_cfg, currency=currency)
    except ValueError as exc:
        st.error(str(exc))
        return

    weight_col = _weight_column(valid_df)
    curves = compute_psm_curves(valid_df, grid_details.prices, weight_col=weight_col)
    kpi_result = compute_psm_kpis(curves)
    figure = make_psm_figure(curves, kpi_result)

    increment_label = "None" if grid_details.increment is None else f"{grid_details.increment:g}"
    st.caption(
        f"Grid increment used: {increment_label} | "
        f"grid_min={grid_details.min_price:.2f} | "
        f"grid_max={grid_details.max_price:.2f} | "
        f"grid_step={grid_details.step:.2f}"
    )
    st.plotly_chart(figure, use_container_width=True)

    kpi_dict = kpi_result.as_dict()
    _render_kpi_cards(currency + " ", kpi_dict)

    st.subheader("Quality Control")
    qc_df = qc.as_frame()
    qc_df["excluded_psm_n"] = int((~valid_mask).sum())
    st.dataframe(qc_df, use_container_width=True)

    nms_result = None
    if _has_nms_columns(valid_df):
        nms_result = compute_nms(
            valid_df,
            grid_details.prices,
            weight_col=weight_col,
            puki_threshold=puki_threshold,
        )
        st.subheader("NMS Trial + Revenue")
        st.plotly_chart(make_nms_figure(nms_result), use_container_width=True)
        col_n1, col_n2, col_n3 = st.columns(3)
        col_n1.metric("MaxTrial Price", f"{currency} {nms_result.max_trial_price:.2f}")
        col_n2.metric("MaxRevenue Price", f"{currency} {nms_result.max_revenue_price:.2f}")
        col_n3.metric("NMS Included N", str(nms_result.included_n))
        if nms_result.filter_note:
            st.caption(nms_result.filter_note)
    else:
        st.info("PI columns are missing. NMS chart is not available for this selection.")

    st.session_state["psm_analysis_payload"] = {
        "product_id": selected_product,
        "segment": selected_segment,
        "currency": currency,
        "group_df": group_df,
        "valid_df": valid_df,
        "curves": curves,
        "kpis": kpi_dict,
        "kpi_result": kpi_result,
        "nms_result": nms_result,
        "puki_threshold": puki_threshold,
        "grid": {
            "min_price": grid_details.min_price,
            "max_price": grid_details.max_price,
            "step": grid_details.step,
            "increment": grid_details.increment,
            "snapped": grid_details.snapped,
        },
        "qc": qc_df,
    }


if __name__ == "__main__":
    main()
