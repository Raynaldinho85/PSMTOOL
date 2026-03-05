from __future__ import annotations

import importlib.util

import streamlit as st

from psm_tool.config import GridConfig
from psm_tool.io.validate import (
    OPTIONAL_COLUMNS,
    PI_UNIT_NORMALIZED_WARNING,
    PI_UNIT_TINY_WARNING,
    RECOMMENDED_COLUMNS,
    REQUIRED_COLUMNS,
    template_columns,
)
from psm_tool.ui.knowledge_content import (
    get_knowledge_markdown_de,
    get_knowledge_markdown_en,
)
from psm_tool.ui.page_nav import render_page_nav_top
from psm_tool.ui.style import inject_base_styles, render_notice

TAB_ORDER = [
    "Overview",
    "PSM (Price Sensitivity Meter)",
    "NMS (Newton-Miller-Smith)",
    "Quality & Grid",
    "Exports & Privacy",
    "FAQ",
]

ORDERING_RULE = "too_cheap < bargain < expensive_acceptable < too_expensive"
INTERSECTION_STATUSES = ["clean", "interval", "closest"]


def _sav_available() -> bool:
    return importlib.util.find_spec("pyreadstat") is not None


def _config_snapshot() -> dict:
    grid_cfg = GridConfig()
    return {
        "default_currency_snap": dict(grid_cfg.currency_snap),
        "supported_columns": template_columns(),
        "required_columns": sorted(REQUIRED_COLUMNS),
        "recommended_columns": sorted(RECOMMENDED_COLUMNS),
        "optional_columns": sorted(OPTIONAL_COLUMNS),
        "ordering_rule": ORDERING_RULE,
        "intersection_statuses": INTERSECTION_STATUSES,
        "pi_normalization_note_available": bool(PI_UNIT_NORMALIZED_WARNING),
        "pi_tiny_note_available": bool(PI_UNIT_TINY_WARNING),
    }


def _render_tab_content(
    *,
    tab_name: str,
    markdown_map: dict[str, str],
    language: str,
    config_snapshot: dict,
    sav_available: bool,
) -> None:
    st.markdown(markdown_map[tab_name])

    if tab_name == "Overview":
        render_notice(
            ("Deterministic only: calculations and explanations are static and rule-based.")
            if language == "English"
            else "Deterministisch: Berechnungen und Erlaeuterungen sind regelbasiert."
        )
        with st.expander(
            "Input schema details" if language == "English" else "Input-Schema im Detail",
            expanded=False,
        ):
            st.markdown(
                "Required columns: " + ", ".join(config_snapshot["required_columns"])
                if language == "English"
                else "Pflichtspalten: " + ", ".join(config_snapshot["required_columns"])
            )
            st.markdown(
                "Recommended columns: " + ", ".join(config_snapshot["recommended_columns"])
                if language == "English"
                else "Empfohlene Spalten: " + ", ".join(config_snapshot["recommended_columns"])
            )
            st.markdown(
                "Optional columns: " + ", ".join(config_snapshot["optional_columns"])
                if language == "English"
                else "Optionale Spalten: " + ", ".join(config_snapshot["optional_columns"])
            )
            if sav_available:
                render_notice(
                    "SAV support is enabled in this environment."
                    if language == "English"
                    else "SAV-Unterstuetzung ist in dieser Umgebung aktiv.",
                )
            else:
                render_notice(
                    "SAV support is optional; not installed in this environment."
                    if language == "English"
                    else "SAV-Unterstuetzung ist optional und in dieser Umgebung nicht installiert."
                )

    if tab_name == "PSM (Price Sensitivity Meter)":
        render_notice(
            f"Validity rule used by code: `{config_snapshot['ordering_rule']}`"
            if language == "English"
            else f"Plausi-Regel im Code: `{config_snapshot['ordering_rule']}`"
        )
        with st.expander(
            "Intersection statuses implemented"
            if language == "English"
            else "Implementierte Schnittpunkt-Status",
            expanded=False,
        ):
            for status in config_snapshot["intersection_statuses"]:
                st.markdown(f"- {status}")

    if tab_name == "NMS (Newton-Miller-Smith)":
        if config_snapshot["pi_normalization_note_available"]:
            render_notice(
                (
                    "PI unit invariant: internal PI is percent 0..100. "
                    "Fraction-scale input can be normalized with warning notes."
                )
                if language == "English"
                else (
                    "PI-Invariante: intern ist PI Prozent 0..100. "
                    "Fraction-Input kann mit Hinweis normalisiert werden."
                )
            )
        else:
            render_notice(
                ("PI unit expectation is 0..100 percent. Fraction input can compress PI curves.")
                if language == "English"
                else "Erwartete PI-Einheit ist 0..100 Prozent. Fraction-Input kann PI komprimieren."
            )

    if tab_name == "Quality & Grid":
        render_notice(
            "Default currency snapping values are read from config."
            if language == "English"
            else "Default-Currency-Snapping wird aus der Config gelesen."
        )
        with st.expander(
            "Current snap mapping" if language == "English" else "Aktuelles Snap-Mapping",
            expanded=False,
        ):
            for currency, increment in config_snapshot["default_currency_snap"].items():
                st.markdown(f"- {currency}: {increment:g}")

    if tab_name == "Exports & Privacy":
        render_notice(
            ("PPTX image export requires a working Chrome/Chromium runtime.")
            if language == "English"
            else "PPTX-Bildexport benoetigt eine funktionierende Chrome/Chromium-Runtime."
        )

    if tab_name == "FAQ":
        with st.expander(
            "Quick pre-share checks" if language == "English" else "Schnelle Checks vor dem Teilen",
            expanded=False,
        ):
            if language == "English":
                st.markdown("- Verify PI units and PI source mode.")
                st.markdown("- Verify segment/currency consistency.")
                st.markdown("- Verify export preflight before PPTX generation.")
            else:
                st.markdown("- PI-Einheiten und PI-Quelle pruefen.")
                st.markdown("- Segment-/Waehrungskonsistenz pruefen.")
                st.markdown("- Export-Preflight vor PPTX pruefen.")


def main() -> None:
    inject_base_styles(max_width=2800)
    st.markdown('<p class="psm-page-eyebrow">Reference</p>', unsafe_allow_html=True)
    st.title("Knowledge & Methodology")
    render_page_nav_top("knowledge")

    language = st.radio(
        "Language / Sprache",
        options=["English", "Deutsch"],
        horizontal=True,
    )

    config_snapshot = _config_snapshot()
    sav_available = _sav_available()
    if language == "English":
        markdown_map = get_knowledge_markdown_en(config_snapshot, sav_available)
    else:
        markdown_map = get_knowledge_markdown_de(config_snapshot, sav_available)

    tabs = st.tabs(TAB_ORDER)
    for tab, tab_name in zip(tabs, TAB_ORDER, strict=False):
        with tab:
            _render_tab_content(
                tab_name=tab_name,
                markdown_map=markdown_map,
                language=language,
                config_snapshot=config_snapshot,
                sav_available=sav_available,
            )

    st.caption(
        "Back to Results: open page '2 Results' from the sidebar."
        if language == "English"
        else "Zurueck zu Results: oeffne Seite '2 Results' in der Sidebar."
    )


if __name__ == "__main__":
    main()
