from __future__ import annotations

from pathlib import Path

import streamlit as st

from psm_tool.core.nms import NMSResult
from psm_tool.core.turnover_index import ProfitProxyResult, TurnoverIndexResult
from psm_tool.plots.render_static import BrowserPreflightError, check_kaleido_browser
from psm_tool.report.excel_export import build_excel_report
from psm_tool.report.payload_builder import build_export_payload_from_dataset
from psm_tool.report.pptx_builder import build_pptx_report
from psm_tool.ui.page_nav import render_page_nav_bottom, render_page_nav_top
from psm_tool.ui.style import inject_base_styles, render_notice


def _materialize_payload(analysis_payload: dict) -> dict:
    export_analysis = {
        "product_id": analysis_payload["product_id"],
        "segment": analysis_payload["segment"],
        "currency": analysis_payload["currency"],
        "curves": analysis_payload["curves"],
        "kpis": analysis_payload["kpis"],
        "kpi_result": analysis_payload["kpi_result"],
        "outlier_settings": analysis_payload.get("outlier_settings", {}),
        "outlier_stats": analysis_payload.get("outlier_stats", {}),
    }
    if "nms_result" in analysis_payload and isinstance(analysis_payload["nms_result"], NMSResult):
        export_analysis["nms_result"] = analysis_payload["nms_result"]
    if "turnover_index_result" in analysis_payload and isinstance(
        analysis_payload["turnover_index_result"], TurnoverIndexResult
    ):
        export_analysis["turnover_index_result"] = analysis_payload["turnover_index_result"]
    if "profit_proxy_result" in analysis_payload and isinstance(
        analysis_payload["profit_proxy_result"], ProfitProxyResult
    ):
        export_analysis["profit_proxy_result"] = analysis_payload["profit_proxy_result"]
    export_analysis["unit_cost"] = analysis_payload.get("unit_cost")
    export_analysis["turnover_source"] = analysis_payload.get("turnover_source")
    return {"analyses": [export_analysis]}


def _build_bulk_payload(analysis_payload: dict) -> dict:
    input_df = st.session_state.get("psm_input_df")
    if input_df is None:
        return _materialize_payload(analysis_payload)
    pi_ladder_df = st.session_state.get("psm_pi_ladder_df")
    outlier_settings = analysis_payload.get("outlier_settings", {})
    payload = build_export_payload_from_dataset(
        input_df,
        pi_ladder_df=pi_ladder_df,
        plausibility_filter_applied=bool(analysis_payload.get("plausibility_filter_applied", True)),
        outlier_enabled=bool(outlier_settings.get("enabled", False)),
        outlier_level=str(outlier_settings.get("level", "medium")),
        puki_threshold=int(analysis_payload.get("puki_threshold", 2)),
        snap_enabled=True,  # export follows auto grid behavior
        unit_cost_by_key=dict(st.session_state.get("unit_cost_by_product", {})),
        economics_enabled_by_key=dict(st.session_state.get("economics_enabled_by_product", {})),
    )
    if not payload.get("analyses"):
        return _materialize_payload(analysis_payload)
    return payload


def main() -> None:
    inject_base_styles(max_width=2800)
    st.title("3. Export")
    render_page_nav_top("export")
    analysis_payload = st.session_state.get("psm_analysis_payload")
    dataset_loaded = st.session_state.get("psm_input_df") is not None
    if analysis_payload is None:
        if dataset_loaded:
            render_notice(
                "No analysis available yet. Start from Upload to change data, "
                "then run Results to compute KPIs before export."
            )
            nav_col1, nav_col2 = st.columns(2)
            if nav_col1.button("Go to Upload", width="stretch", key="export_go_upload_btn"):
                st.switch_page("pages/1_upload.py")
            if nav_col2.button(
                "Go to Results",
                width="stretch",
                key="export_go_results_btn",
            ):
                st.switch_page("pages/2_results.py")
        else:
            render_notice(
                "No dataset loaded. Run page '1 Upload' first (or again) to enable "
                "Results and Export."
            )
            if st.button("Go to Upload", width="stretch", key="export_go_upload_only_btn"):
                st.switch_page("pages/1_upload.py")
        render_page_nav_bottom("export")
        return

    st.caption("Exports are generated in-memory and are not written to disk by default.")
    with st.container(border=True):
        st.markdown(
            "This page exports all available Product x Country combinations using "
            "the current filter configuration and auto-grid behavior."
        )

    preflight_ok = True
    preflight_message = "Static export preflight succeeded."
    try:
        check_kaleido_browser()
    except BrowserPreflightError as exc:
        preflight_ok = False
        preflight_message = str(exc)
    except Exception as exc:
        preflight_ok = False
        preflight_message = f"Static export preflight failed: {exc}"

    if preflight_ok:
        render_notice(preflight_message, tone="positive")
    else:
        render_notice(preflight_message)

    payload = _build_bulk_payload(analysis_payload)
    template_path = Path("assets/template.pptx")
    use_template = template_path.exists()
    analyses = payload.get("analyses", [])
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("PPTX template", "yes" if use_template else "no")
        col2.metric("Product x Country", str(len(analyses)))
        col3.metric("Export mode", "Auto-grid batch")

    if not preflight_ok:
        render_notice("Resolve static rendering preflight errors before generating export files.")
        return

    pptx_bytes = build_pptx_report(payload, template_path=template_path if use_template else None)
    excel_bytes = build_excel_report(payload)

    product = analysis_payload["product_id"]
    segment = analysis_payload["segment"]

    export_col1, export_col2 = st.columns(2)
    export_col1.download_button(
        "Download PPTX report",
        data=pptx_bytes,
        file_name=f"psm_report_{product}_{segment}.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        width="stretch",
    )
    export_col2.download_button(
        "Download Excel export",
        data=excel_bytes,
        file_name=f"psm_export_{product}_{segment}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    render_page_nav_bottom("export")


if __name__ == "__main__":
    main()
