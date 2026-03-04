from __future__ import annotations

import streamlit as st

from psm_tool.config import AppConfig


def _check_password(config: AppConfig) -> None:
    if not config.app_password:
        return

    provided = st.text_input("Application password", type="password")
    if provided != config.app_password:
        st.warning("Enter a valid password to continue.")
        st.stop()


def _initialize_state() -> None:
    defaults = {
        "psm_input_df": None,
        "psm_validation_errors": [],
        "psm_validation_warnings": [],
        "psm_analysis_payload": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def main() -> None:
    config = AppConfig()
    st.set_page_config(page_title="PSM Tool", page_icon=":bar_chart:", layout="wide")
    _initialize_state()

    st.title("PSM Tool")
    st.caption("Van Westendorp Price Sensitivity Meter + optional NMS extension")
    st.info("Privacy: uploaded files are processed in-memory and are not stored on disk.")

    _check_password(config)

    st.markdown(
        """
Use the page navigation in the sidebar:

- **1 Upload**: load a CSV/XLSX/SAV file, download templates, or load synthetic demo data.
- **2 Results**: calculate PSM curves/KPIs and inspect quality checks.
- **3 Export**: generate PPTX/Excel outputs in-memory for download.
"""
    )
    if config.demo_mode:
        st.warning(
            "DEMO_MODE is enabled. Strict upload limits are active "
            "and raw respondent-level output is hidden."
        )


if __name__ == "__main__":
    main()
