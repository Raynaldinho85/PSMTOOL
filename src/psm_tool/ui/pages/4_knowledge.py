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
from psm_tool.ui.style import inject_base_styles

TAB_ORDER = [
    "Overview",
    "PSM (Price Sensitivity Meter)",
    "Purchase Intention & Turnover",
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
        st.info(
            (
                "Deterministic behavior only: all calculations and explanations "
                "are static and rule-based."
            )
            if language == "English"
            else (
                "Deterministisches Verhalten: alle Berechnungen und Erklärungen sind regelbasiert."
            )
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
                st.info("SAV support is enabled in this environment.")
            else:
                st.warning(
                    "SAV support is optional; not installed in this environment."
                    if language == "English"
                    else "SAV-Unterstützung ist optional und in dieser Umgebung nicht installiert."
                )

    if tab_name == "PSM (Price Sensitivity Meter)":
        st.info(
            f"Validity rule used by code: `{config_snapshot['ordering_rule']}`"
            if language == "English"
            else f"Im Code verwendete Plausi-Regel: `{config_snapshot['ordering_rule']}`"
        )
        with st.expander(
            "Intersection statuses in this tool"
            if language == "English"
            else "Schnittpunkt-Status in diesem Tool",
            expanded=False,
        ):
            st.markdown("- clean")
            st.markdown("- interval")
            st.markdown("- closest")

    if tab_name == "Purchase Intention & Turnover":
        if config_snapshot["pi_normalization_note_available"]:
            st.info(
                (
                    "PI unit handling: internally PI is treated as 0..100 percent. "
                    "When clear fraction-scale input (0..1) is detected, the tool can normalize "
                    "it and report a warning note."
                )
                if language == "English"
                else (
                    "PI-Einheiten: intern wird PI als Prozent 0..100 behandelt. "
                    "Wenn klarer 0..1-Input erkannt wird, kann das Tool normalisieren und "
                    "einen Hinweis ausgeben."
                )
            )
        else:
            st.warning(
                (
                    "PI unit expectation: 0..100 percent. Fraction input (0..1) can compress PI "
                    "curves and should be corrected before interpretation."
                )
                if language == "English"
                else (
                    "Erwartete PI-Einheit: Prozent 0..100. 0..1-Eingaben können PI-Kurven "
                    "komprimieren und sollten vor der Interpretation korrigiert werden."
                )
            )
        with st.expander(
            "Modeled vs measured PI curve"
            if language == "English"
            else "Modellierte vs. gemessene PI-Kurve",
            expanded=False,
        ):
            st.markdown(
                (
                    "Without an explicit ladder, the curve is reconstructed "
                    "from respondent anchors "
                    "using a deterministic piecewise-linear model."
                )
                if language == "English"
                else (
                    "Ohne explizite Preisleiter wird die Kurve aus Respondent-Ankern über ein "
                    "deterministisches piecewise-lineares Modell rekonstruiert."
                )
            )

    if tab_name == "Quality & Grid":
        st.info(
            "Current default currency snapping values are loaded from configuration."
            if language == "English"
            else "Die aktuellen Currency-Snapping-Defaults werden aus der Konfiguration geladen."
        )
        with st.expander(
            "Current config snapshot" if language == "English" else "Aktueller Config-Snapshot",
            expanded=False,
        ):
            for currency, increment in config_snapshot["default_currency_snap"].items():
                st.markdown(f"- {currency}: {increment:g}")

    if tab_name == "Exports & Privacy":
        st.warning(
            (
                "For static chart export (PNG into PPTX), a working "
                "Chrome/Chromium setup is required."
            )
            if language == "English"
            else (
                "Für statische Chart-Exports (PNG in PPTX) ist eine funktionierende "
                "Chrome/Chromium-Umgebung erforderlich."
            )
        )

    if tab_name == "FAQ":
        with st.expander(
            "Practical checks before sharing results"
            if language == "English"
            else "Praktische Checks vor dem Teilen von Ergebnissen",
            expanded=False,
        ):
            if language == "English":
                st.markdown("- Verify PI units (`pi_bargain_pct`, `pi_expensive_pct`).")
                st.markdown("- Verify segment/currency consistency.")
                st.markdown("- Verify export preflight before PPTX generation.")
            else:
                st.markdown("- PI-Einheiten (`pi_bargain_pct`, `pi_expensive_pct`) prüfen.")
                st.markdown("- Segment-/Währungskonsistenz prüfen.")
                st.markdown("- Export-Preflight vor PPTX-Generierung prüfen.")


def main() -> None:
    inject_base_styles(max_width=1380)
    st.markdown('<p class="psm-page-eyebrow">Reference</p>', unsafe_allow_html=True)
    st.title("Knowledge & Methodology")

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
        else "Zurück zu Results: öffne Seite '2 Results' in der Sidebar."
    )


if __name__ == "__main__":
    main()
