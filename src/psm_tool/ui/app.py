from __future__ import annotations

import streamlit as st

from psm_tool.config import AppConfig
from psm_tool.ui.style import inject_base_styles


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
        "psm_pi_ladder_df": None,
        "psm_validation_errors": [],
        "psm_validation_warnings": [],
        "psm_analysis_payload": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def main() -> None:
    config = AppConfig()
    st.set_page_config(page_title="PSM Tool", page_icon=":bar_chart:", layout="wide")
    inject_base_styles(max_width=1420)
    _initialize_state()

    st.title("PSM Tool")
    st.caption("Van Westendorp PSM with optional Newton-Miller-Smith Trial + Revenue extension.")

    with st.container(border=True):
        st.markdown(
            "This app analyzes uploaded pricing survey data fully in-memory. "
            "No raw upload files are written to disk by default."
        )

    _check_password(config)

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("**1 Upload**")
            st.markdown(
                "<p class='psm-muted'>Load CSV/XLSX/SAV, validate template, or use demo data.</p>",
                unsafe_allow_html=True,
            )
    with col2:
        with st.container(border=True):
            st.markdown("**2 Results**")
            st.markdown(
                "<p class='psm-muted'>Run PSM + optional NMS, review KPIs and quality checks.</p>",
                unsafe_allow_html=True,
            )
    with col3:
        with st.container(border=True):
            st.markdown("**3 Export**")
            st.markdown(
                "<p class='psm-muted'>Download PowerPoint and Excel exports "
                "generated in-memory.</p>",
                unsafe_allow_html=True,
            )
    if config.demo_mode:
        st.warning(
            "DEMO_MODE is enabled. Strict upload limits are active "
            "and raw respondent-level output is hidden."
        )


if __name__ == "__main__":
    main()
