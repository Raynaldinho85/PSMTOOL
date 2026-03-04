from __future__ import annotations

from pathlib import Path

import streamlit as st

from psm_tool.core.nms import NMSResult
from psm_tool.core.turnover_index import TurnoverIndexResult
from psm_tool.plots.render_static import BrowserPreflightError, check_kaleido_browser
from psm_tool.report.excel_export import build_excel_report
from psm_tool.report.pptx_builder import build_pptx_report
from psm_tool.ui.style import inject_base_styles


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
    export_analysis["turnover_source"] = analysis_payload.get("turnover_source")
    return {"analyses": [export_analysis]}


def main() -> None:
    inject_base_styles(max_width=1380)
    st.title("3. Export")
    analysis_payload = st.session_state.get("psm_analysis_payload")
    if analysis_payload is None:
        st.warning("No analysis available. Run page '2 Results' first.")
        return

    st.caption("Exports are generated in-memory and are not written to disk by default.")
    with st.container(border=True):
        st.markdown(
            "This page exports exactly the currently visible analysis state "
            "(selection, filters, and KPI values)."
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
        st.success(preflight_message)
    else:
        st.error(preflight_message)

    payload = _materialize_payload(analysis_payload)
    template_path = Path("assets/template.pptx")
    use_template = template_path.exists()
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("PPTX template", "yes" if use_template else "no")
        col2.metric("Product", str(analysis_payload["product_id"]))
        col3.metric("Segment", str(analysis_payload["segment"]))

    if not preflight_ok:
        st.info("Resolve static rendering preflight errors before generating export files.")
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
        use_container_width=True,
    )
    export_col2.download_button(
        "Download Excel export",
        data=excel_bytes,
        file_name=f"psm_export_{product}_{segment}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
