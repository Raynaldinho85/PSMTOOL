from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from psm_tool.i18n import get_language, set_language, t


@dataclass(frozen=True, slots=True)
class PageNavItem:
    key: str
    path: str
    label_key: str


PAGE_ORDER: list[PageNavItem] = [
    PageNavItem(key="app", path="app.py", label_key="nav.app"),
    PageNavItem(key="upload", path="pages/1_upload.py", label_key="nav.upload"),
    PageNavItem(key="results", path="pages/2_results.py", label_key="nav.results"),
    PageNavItem(key="export", path="pages/3_export.py", label_key="nav.export"),
    PageNavItem(key="knowledge", path="pages/4_knowledge.py", label_key="nav.knowledge"),
]


def _current_index(current_key: str) -> int | None:
    for idx, item in enumerate(PAGE_ORDER):
        if item.key == current_key:
            return idx
    return None


def _neighbors(current_key: str) -> tuple[PageNavItem | None, PageNavItem | None]:
    idx = _current_index(current_key)
    if idx is None:
        return None, None
    prev_item = PAGE_ORDER[idx - 1] if idx > 0 else None
    next_item = PAGE_ORDER[idx + 1] if idx < len(PAGE_ORDER) - 1 else None
    return prev_item, next_item


def render_language_switch() -> None:
    language = get_language()
    st.sidebar.markdown("<div style='height: 0.55rem;'></div>", unsafe_allow_html=True)
    switch_container = st.sidebar.container()
    col_en, col_de = switch_container.columns([1, 1], gap="small")
    with col_en:
        if st.button(
            "EN",
            key="app_language_en_btn",
            help="English",
            type="primary" if language == "en" else "secondary",
            width="content",
        ):
            set_language("en")
    with col_de:
        if st.button(
            "DE",
            key="app_language_de_btn",
            help="Deutsch",
            type="primary" if language == "de" else "secondary",
            width="content",
        ):
            set_language("de")


def render_page_nav_top(current_key: str) -> None:
    render_language_switch()
    prev_item, _next_item = _neighbors(current_key)
    if prev_item is None:
        return
    st.page_link(
        prev_item.path,
        label=f"{t('nav.previous')}: {t(prev_item.label_key)}",
        width="content",
    )


def render_page_nav_bottom(current_key: str) -> None:
    _prev_item, next_item = _neighbors(current_key)
    if current_key == "app":
        render_language_switch()
    if current_key == "app" and next_item is None:
        return
    if next_item is None:
        return
    st.page_link(
        next_item.path,
        label=f"{t('nav.next')}: {t(next_item.label_key)}",
        width="content",
    )
