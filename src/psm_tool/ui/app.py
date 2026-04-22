from __future__ import annotations

import streamlit as st

from psm_tool.i18n import DEFAULT_LANGUAGE, get_language, tr
from psm_tool.ui.auth import require_auth
from psm_tool.ui.page_nav import render_page_nav_bottom
from psm_tool.ui.style import inject_base_styles


def _initialize_state() -> None:
    defaults = {
        "psm_input_df": None,
        "psm_pi_ladder_df": None,
        "psm_input_source": None,
        "unit_cost_by_product": {},
        "psm_validation_errors": [],
        "psm_validation_warnings": [],
        "psm_analysis_payload": None,
        "tested_price_by_key": {},
        "tested_price_active_by_key": {},
        "app_language": DEFAULT_LANGUAGE,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def main() -> None:
    st.set_page_config(page_title="PRICEY", page_icon=":bar_chart:", layout="wide")
    inject_base_styles(max_width=2800)
    _initialize_state()
    require_auth()
    language = get_language()

    st.markdown(
        f'<p class="psm-page-eyebrow">{tr("Pricing Research Toolkit", language)}</p>',
        unsafe_allow_html=True,
    )
    st.title(tr("PRICEY", language))
    st.caption(
        tr(
            (
                "Pricey - Pricing Research Toolkit - Measure price "
                "perception. Simulate demand. Find the optimal price."
            ),
            language,
        )
    )

    with st.container(border=True):
        st.markdown(
            tr(
                (
                    "This app analyzes uploaded pricing survey data fully "
                    "in-memory. No raw upload files are written to disk by "
                    "default."
                ),
                language,
            )
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown(
                (
                    "<div class='psm-step-card'>"
                    f"<div class='psm-card-title'>{tr('1 Upload', language)}</div>"
                    "<p class='psm-card-copy'>"
                    f"{tr('Load CSV/XLSX, validate template, or use demo data.', language)}"
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
                    f"<div class='psm-card-title'>{tr('2 Results', language)}</div>"
                    "<p class='psm-card-copy'>"
                    f"{tr('Run PSM + optional NMS, review KPIs and quality checks.', language)}"
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
                    f"<div class='psm-card-title'>{tr('3 Export', language)}</div>"
                    "<p class='psm-card-copy'>"
                    f"{tr('Download PowerPoint and Excel exports generated in-memory.', language)}"
                    "</p>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
    render_page_nav_bottom("app")


if __name__ == "__main__":
    main()
