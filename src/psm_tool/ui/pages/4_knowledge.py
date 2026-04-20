from __future__ import annotations

import importlib.util

import streamlit as st

from psm_tool.config import GridConfig
from psm_tool.i18n import get_language, t, tr
from psm_tool.i18n.knowledge import get_knowledge_markdown
from psm_tool.io.validate import (
    OPTIONAL_COLUMNS,
    PI_UNIT_NORMALIZED_WARNING,
    PI_UNIT_TINY_WARNING,
    RECOMMENDED_COLUMNS,
    REQUIRED_COLUMNS,
    template_columns,
)
from psm_tool.ui.auth import require_auth
from psm_tool.ui.page_nav import render_page_nav_top
from psm_tool.ui.style import inject_base_styles, render_notice

TAB_SPECS = [
    ("Overview", "knowledge.tab.overview"),
    ("PSM (Price Sensitivity Meter)", "knowledge.tab.psm"),
    ("NMS (Newton-Miller-Smith)", "knowledge.tab.nms"),
    ("Quality & Grid", "knowledge.tab.quality_grid"),
    ("Exports & Privacy", "knowledge.tab.exports_privacy"),
    ("FAQ", "knowledge.tab.faq"),
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
        render_notice(t("knowledge.notice.deterministic", language))
        with st.expander(
            t("knowledge.expander.input_schema", language),
            expanded=False,
        ):
            st.markdown(
                t(
                    "knowledge.schema.required",
                    language,
                    columns=", ".join(config_snapshot["required_columns"]),
                )
            )
            st.markdown(
                t(
                    "knowledge.schema.recommended",
                    language,
                    columns=", ".join(config_snapshot["recommended_columns"]),
                )
            )
            st.markdown(
                t(
                    "knowledge.schema.optional",
                    language,
                    columns=", ".join(config_snapshot["optional_columns"]),
                )
            )
            render_notice(
                tr(
                    (
                        "SAV uploads are intentionally disabled in the app so uploaded "
                        "files remain fully in-memory."
                    ),
                    language,
                )
            )

    if tab_name == "PSM (Price Sensitivity Meter)":
        render_notice(
            t(
                "knowledge.notice.validity_rule",
                language,
                ordering_rule=config_snapshot["ordering_rule"],
            )
        )
        with st.expander(
            t("knowledge.expander.intersection_statuses", language),
            expanded=False,
        ):
            for status in config_snapshot["intersection_statuses"]:
                st.markdown(f"- {status}")

    if tab_name == "NMS (Newton-Miller-Smith)":
        if config_snapshot["pi_normalization_note_available"]:
            render_notice(t("knowledge.notice.pi_normalized", language))
        else:
            render_notice(t("knowledge.notice.pi_expected", language))

    if tab_name == "Quality & Grid":
        render_notice(t("knowledge.notice.currency_snap", language))
        with st.expander(
            t("knowledge.expander.snap_mapping", language),
            expanded=False,
        ):
            for currency, increment in config_snapshot["default_currency_snap"].items():
                st.markdown(f"- {currency}: {increment:g}")

    if tab_name == "Exports & Privacy":
        render_notice(t("knowledge.notice.pptx_runtime", language))

    if tab_name == "FAQ":
        with st.expander(
            t("knowledge.expander.pre_share_checks", language),
            expanded=False,
        ):
            st.markdown(t("knowledge.faq.check_pi_units", language))
            st.markdown(t("knowledge.faq.check_segment_currency", language))
            st.markdown(t("knowledge.faq.check_export_preflight", language))


def main() -> None:
    require_auth()
    inject_base_styles(max_width=2800)
    language = get_language()
    st.markdown(
        f'<p class="psm-page-eyebrow">{t("knowledge.eyebrow", language)}</p>',
        unsafe_allow_html=True,
    )
    st.title(t("knowledge.title", language))
    render_page_nav_top("knowledge")

    config_snapshot = _config_snapshot()
    sav_available = _sav_available()
    markdown_map = get_knowledge_markdown(language, config_snapshot, sav_available)

    tab_names = [t(label_key, language) for _tab_name, label_key in TAB_SPECS]
    tabs = st.tabs(tab_names)
    for tab, (tab_name, _label_key) in zip(tabs, TAB_SPECS, strict=False):
        with tab:
            _render_tab_content(
                tab_name=tab_name,
                markdown_map=markdown_map,
                language=language,
                config_snapshot=config_snapshot,
                sav_available=sav_available,
            )

    st.caption(t("knowledge.caption.back_results", language))


if __name__ == "__main__":
    main()
