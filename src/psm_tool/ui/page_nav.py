from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True, slots=True)
class PageNavItem:
    key: str
    path: str
    label: str


PAGE_ORDER: list[PageNavItem] = [
    PageNavItem(key="app", path="app.py", label="App"),
    PageNavItem(key="upload", path="pages/1_upload.py", label="Upload"),
    PageNavItem(key="results", path="pages/2_results.py", label="Results"),
    PageNavItem(key="export", path="pages/3_export.py", label="Export"),
    PageNavItem(key="knowledge", path="pages/4_knowledge.py", label="Knowledge"),
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


def render_page_nav_top(current_key: str) -> None:
    prev_item, _next_item = _neighbors(current_key)
    if prev_item is None:
        return
    st.page_link(
        prev_item.path,
        label=f"↑ {prev_item.label}",
        width="content",
    )


def render_page_nav_bottom(current_key: str) -> None:
    _prev_item, next_item = _neighbors(current_key)
    if next_item is None:
        return
    st.page_link(
        next_item.path,
        label=f"{next_item.label} ↓",
        width="content",
    )
