from __future__ import annotations

import streamlit as st

BASE_STYLE_TEMPLATE = """
<style>
:root {{
    --psm-accent: #f59e0b;
    --psm-accent-soft: rgba(245, 158, 11, 0.10);
    --psm-accent-soft-2: rgba(245, 158, 11, 0.03);
    --psm-muted: #57534e;
    --psm-border: #e7e5e4;
    --psm-surface: #ffffff;
    --psm-radius: 12px;
}}

section.main > div.block-container {{
    max-width: {max_width}px;
    padding-top: 0.9rem;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
    padding-bottom: 1.75rem;
}}

h1 {{
    font-size: 2.0rem !important;
    line-height: 1.2 !important;
    margin-bottom: 0.3rem !important;
}}

h2 {{
    font-size: 1.45rem !important;
    line-height: 1.25 !important;
}}

h3 {{
    font-size: 1.08rem !important;
    line-height: 1.3 !important;
    letter-spacing: 0.01em;
}}

div[data-testid="stCaptionContainer"] p {{
    color: var(--psm-muted) !important;
    font-size: 0.88rem !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: var(--psm-radius);
    border: 1px solid var(--psm-border) !important;
    background: linear-gradient(
        90deg,
        var(--psm-accent-soft) 0%,
        var(--psm-accent-soft-2) 52%,
        #f5f5f4 100%
    );
}}

div[data-testid="stMetric"] {{
    background: var(--psm-surface);
    border: 1px solid var(--psm-border);
    border-radius: 10px;
    padding: 0.55rem 0.75rem;
}}

div[data-testid="stMetricLabel"] p {{
    font-size: 0.76rem !important;
    color: #78716c !important;
}}

div[data-testid="stMetricValue"] {{
    font-size: 1.15rem !important;
    line-height: 1.2 !important;
}}

.psm-page-eyebrow {{
    color: var(--psm-muted);
    font-size: 0.82rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 0.2rem;
}}

.psm-card-title {{
    color: #1c1917;
    font-size: 1.02rem;
    font-weight: 650;
    margin-bottom: 0.2rem;
}}

.psm-card-copy {{
    color: var(--psm-muted);
    font-size: 0.9rem;
    line-height: 1.4;
    margin: 0;
}}

.psm-muted {{
    color: var(--psm-muted);
    font-size: 0.92rem;
}}

.psm-context-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.6rem;
}}

.psm-context-chip {{
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid var(--psm-border);
    border-radius: 10px;
    padding: 0.45rem 0.65rem;
}}

.psm-context-chip .label {{
    display: block;
    color: #78716c;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}

.psm-context-chip .value {{
    display: block;
    color: #292524;
    font-size: 0.95rem;
    font-weight: 600;
    margin-top: 0.1rem;
}}

.psm-upload-state {{
    color: #292524;
    font-size: 0.92rem;
    margin: 0;
}}

.psm-upload-state strong {{
    color: #1c1917;
}}

@media (max-width: 980px) {{
    .psm-context-grid {{
        grid-template-columns: 1fr;
    }}
}}
</style>
"""


def inject_base_styles(*, max_width: int = 1500) -> None:
    st.markdown(BASE_STYLE_TEMPLATE.format(max_width=max_width), unsafe_allow_html=True)
