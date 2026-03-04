from __future__ import annotations

import streamlit as st

BASE_STYLE_TEMPLATE = """
<style>
section.main > div.block-container {{
    max-width: {max_width}px;
    padding-top: 1.2rem;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
    padding-bottom: 2rem;
}}

div[data-testid="stMetric"] {{
    background: #ffffff;
    border: 1px solid #d6d3d1;
    border-radius: 12px;
    padding: 0.75rem 0.9rem;
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 12px;
}}

.psm-muted {{
    color: #44403c;
    font-size: 0.95rem;
}}
</style>
"""


def inject_base_styles(*, max_width: int = 1500) -> None:
    st.markdown(BASE_STYLE_TEMPLATE.format(max_width=max_width), unsafe_allow_html=True)
