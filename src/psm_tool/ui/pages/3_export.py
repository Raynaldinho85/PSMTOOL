from __future__ import annotations

from pathlib import Path

import streamlit as st

from psm_tool.core.metrics import PSMKPIResult
from psm_tool.core.nms import NMSResult
from psm_tool.plots.render_static import BrowserPreflightError, check_kaleido_browser
from psm_tool.report.excel_export import build_excel_report
from psm_tool.report.pptx_builder import build_pptx_report


def _materialize_payload(analysis_payload: dict) -> dict:
    kpi_result = PSMKPIResult(
        pmi=analysis_payload["kpi_result"].pmi,
        opp=analysis_payload["kpi_result"].opp,
        idp=analysis_payload["kpi_result"].idp,
        pme=analysis_payload["kpi_result"].pme,
        accepted_low=analysis_payload["kpi_result"].accepted_low,
        accepted_high=analysis_payload["kpi_result"].accepted_high,
        price_stress=analysis_payload["kpi_result"].price_stress,
        stress_flag=analysis_payload["kpi_result"].stress_flag,
    )
    export_analysis = {
        "product_id": analysis_payload["product_id"],
        "segment": analysis_payload["segment"],
        "currency": analysis_payload["currency"],
        "curves": analysis_payload["curves"],
        "kpis": analysis_payload["kpis"],
        "kpi_result": kpi_result,
    }
    if "nms_result" in analysis_payload and isinstance(analysis_payload["nms_result"], NMSResult):
        export_analysis["nms_result"] = analysis_payload["nms_result"]
    return {"analyses": [export_analysis]}


def main() -> None:
    st.title("3. Export")
    analysis_payload = st.session_state.get("psm_analysis_payload")
    if analysis_payload is None:
        st.warning("No analysis available. Run page '2 Results' first.")
        return

    st.caption("Exports are generated in-memory and never written to disk by default.")

    try:
        check_kaleido_browser()
    except BrowserPreflightError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Static export preflight failed: {exc}")
        st.stop()

    payload = _materialize_payload(analysis_payload)
    template_path = Path("assets/template.pptx")
    use_template = template_path.exists()
    st.write(f"PPTX template detected: **{'yes' if use_template else 'no'}**")

    pptx_bytes = build_pptx_report(payload, template_path=template_path if use_template else None)
    excel_bytes = build_excel_report(payload)

    product = analysis_payload["product_id"]
    segment = analysis_payload["segment"]
    st.download_button(
        "Download PPTX report",
        data=pptx_bytes,
        file_name=f"psm_report_{product}_{segment}.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    st.download_button(
        "Download Excel export",
        data=excel_bytes,
        file_name=f"psm_export_{product}_{segment}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
