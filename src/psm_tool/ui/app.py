from __future__ import annotations

import streamlit as st

from psm_tool.config import AppConfig
from psm_tool.ui.page_nav import render_page_nav_bottom
from psm_tool.ui.style import inject_base_styles, render_notice


def _check_password(config: AppConfig) -> None:
    if not config.app_password:
        return

    provided = st.text_input("Application password", type="password")
    if provided != config.app_password:
        render_notice("Enter a valid password to continue.")
        st.stop()


def _initialize_state() -> None:
    defaults = {
        "psm_input_df": None,
        "psm_pi_ladder_df": None,
        "psm_input_source": None,
        "unit_cost_by_product": {},
        "psm_validation_errors": [],
        "psm_validation_warnings": [],
        "psm_analysis_payload": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def main() -> None:
    config = AppConfig()
    st.set_page_config(page_title="PRICEY", page_icon=":bar_chart:", layout="wide")
    inject_base_styles(max_width=2800)
    _initialize_state()

    st.markdown('<p class="psm-page-eyebrow">Pricing Research Toolkit</p>', unsafe_allow_html=True)
    st.title("PRICEY")
    st.caption(
        "Pricey - Pricing Research Toolkit - Measure price perception. "
        "Simulate demand. Find the optimal price."
    )

    with st.container(border=True):
        st.markdown(
            "This app analyzes uploaded pricing survey data fully in-memory. "
            "No raw upload files are written to disk by default."
        )

    _check_password(config)

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown(
                (
                    "<div class='psm-step-card'>"
                    "<div class='psm-card-title'>1 Upload</div>"
                    "<p class='psm-card-copy'>"
                    "Load CSV/XLSX/SAV, validate template, or use demo data."
                    "</p>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
    with col2:
        with st.container(border=True):
            st.markdown(
                (
                    "<div class='psm-step-card'>"
                    "<div class='psm-card-title'>2 Results</div>"
                    "<p class='psm-card-copy'>"
                    "Run PSM + optional NMS, review KPIs and quality checks."
                    "</p>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
    with col3:
        with st.container(border=True):
            st.markdown(
                (
                    "<div class='psm-step-card'>"
                    "<div class='psm-card-title'>3 Export</div>"
                    "<p class='psm-card-copy'>"
                    "Download PowerPoint and Excel exports generated in-memory."
                    "</p>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
    if config.demo_mode:
        render_notice(
            "DEMO_MODE is enabled. Strict upload limits are active "
            "and raw respondent-level output is hidden."
        )

    render_page_nav_bottom("app")


if __name__ == "__main__":
    main()
