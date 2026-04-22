from __future__ import annotations

from html import escape

import streamlit as st

BASE_STYLE_TEMPLATE = """
<style>
:root {{
    --psm-accent: #ff5722;
    --psm-positive: #16a34a;
    --psm-accent-soft: rgba(255, 87, 34, 0.10);
    --psm-accent-soft-2: rgba(255, 87, 34, 0.03);
    --psm-sidebar-tint-1: rgba(255, 87, 34, 0.10);
    --psm-sidebar-tint-2: rgba(255, 87, 34, 0.05);
    --psm-sidebar-tint-3: rgba(255, 87, 34, 0.02);
    --psm-muted: #57534e;
    --psm-border: #e7e5e4;
    --psm-surface: #ffffff;
    --psm-radius: 12px;
    --psm-main-gap: 12px;
    --psm-main-max-width: 1100px;
}}

section.main > div.block-container,
div[data-testid="stMainBlockContainer"],
div[data-testid="stAppViewBlockContainer"] > div {{
    max-width: min({max_width}px, var(--psm-main-max-width)) !important;
    width: min(100%, var(--psm-main-max-width)) !important;
    margin-left: var(--psm-main-gap) !important;
    margin-right: auto !important;
    padding-top: 2.35rem;
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

div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"],
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] {{
    font-family: "Source Sans Pro", "Segoe UI", "Helvetica Neue", Arial, sans-serif !important;
}}

div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] p,
div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] li,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] li {{
    font-size: 0.96rem !important;
    line-height: 1.52 !important;
}}

div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] h3 {{
    margin-top: 0.35rem !important;
}}

div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] h1 {{
    font-size: 1.52rem !important;
    line-height: 1.28 !important;
    margin-bottom: 0.55rem !important;
}}

div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] h2 {{
    font-size: 1.20rem !important;
    line-height: 1.34 !important;
    margin-bottom: 0.42rem !important;
}}

div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] h3 {{
    font-size: 1.02rem !important;
    line-height: 1.36 !important;
    margin-bottom: 0.35rem !important;
}}

div[data-testid="stCaptionContainer"] p {{
    color: var(--psm-muted) !important;
    font-size: 0.88rem !important;
}}

div[data-testid="stAlert"] {{
    border: 1px solid rgba(255, 87, 34, 0.33) !important;
    border-radius: 10px !important;
    background: #f5f5f4 !important;
}}

div[data-testid="stAlert"] p {{
    color: var(--psm-accent) !important;
}}

div[data-testid="stAlert"] svg {{
    color: var(--psm-accent) !important;
    fill: var(--psm-accent) !important;
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

div[data-testid="stVerticalBlock"]:has(> div[data-testid="stVerticalBlockBorderWrapper"]) {{
    margin-bottom: 0.85rem;
}}

div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {{
    padding: 0.78rem 0.9rem 0.74rem 0.9rem;
    row-gap: 0.46rem;
}}

div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHeadingWithActionElements"] {{
    margin: 0 0 0.18rem 0 !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] h3 {{
    margin-top: 0 !important;
    margin-bottom: 0.24rem !important;
}}

section[data-testid="stSidebar"] > div:first-child {{
    background: linear-gradient(
        90deg,
        var(--psm-sidebar-tint-1) 0%,
        var(--psm-sidebar-tint-2) 28%,
        var(--psm-sidebar-tint-3) 58%,
        rgba(255, 87, 34, 0) 84%,
        rgba(250, 250, 249, 0) 100%
    ) !important;
}}

section[data-testid="stSidebar"] {{
    border-left: 1px solid rgba(255, 87, 34, 0.75) !important;
    background: transparent !important;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {{
    border-top: none !important;
    box-shadow: none !important;
    background-image: none !important;
}}

section[data-testid="stSidebar"]
div[data-testid="stSidebarUserContent"] > div:first-child,
section[data-testid="stSidebar"]
div[data-testid="stSidebarUserContent"] > div:first-child > div:first-child,
section[data-testid="stSidebar"]
div[data-testid="stSidebarUserContent"]
> div:first-child > div:first-child > div:first-child {{
    border-top: none !important;
    box-shadow: none !important;
    background-image: none !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"]::before,
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"]::after,
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] + div::before,
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] + div::after {{
    content: none !important;
    display: none !important;
    border: 0 !important;
    box-shadow: none !important;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] + div,
section[data-testid="stSidebar"]
div[data-testid="stSidebarNav"] ~ div[data-testid="stSidebarUserContent"] {{
    border-top: none !important;
    box-shadow: none !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: linear-gradient(
        90deg,
        rgba(255, 87, 34, 0.26) 0%,
        rgba(255, 87, 34, 0.15) 28%,
        rgba(255, 87, 34, 0.06) 46%,
        rgba(255, 87, 34, 0.00) 58%,
        rgba(255, 87, 34, 0.00) 100%
    ) !important;
    border-radius: 8px;
    box-shadow: inset 1.5px 0 0 rgba(255, 87, 34, 0.65);
    color: #7c2d12 !important;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] a:hover {{
    background: linear-gradient(
        90deg,
        rgba(120, 120, 120, 0.16) 0%,
        rgba(120, 120, 120, 0.09) 42%,
        rgba(120, 120, 120, 0.00) 62%,
        rgba(120, 120, 120, 0.00) 100%
    ) !important;
    border-radius: 8px;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] a[aria-current="page"]:hover {{
    background: linear-gradient(
        90deg,
        rgba(255, 87, 34, 0.28) 0%,
        rgba(255, 87, 34, 0.17) 30%,
        rgba(255, 87, 34, 0.07) 48%,
        rgba(255, 87, 34, 0.00) 60%,
        rgba(255, 87, 34, 0.00) 100%
    ) !important;
}}

div[data-testid="stFileUploaderDropzone"] {{
    border: 1px dashed rgba(255, 87, 34, 0.45) !important;
    background: linear-gradient(
        90deg,
        rgba(255, 87, 34, 0.08) 0%,
        rgba(255, 87, 34, 0.03) 48%,
        rgba(255, 87, 34, 0.00) 100%
    );
}}

div[data-testid="stFileUploaderDropzone"]:hover {{
    border-color: rgba(255, 87, 34, 0.7) !important;
    background: linear-gradient(
        90deg,
        rgba(255, 87, 34, 0.12) 0%,
        rgba(255, 87, 34, 0.05) 48%,
        rgba(255, 87, 34, 0.00) 100%
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

.psm-kpi-card {{
    background: var(--psm-surface);
    border: 1px solid var(--psm-border);
    border-radius: 10px;
    padding: 0.55rem 0.75rem;
    min-height: 6.35rem;
}}

.psm-kpi-title {{
    color: #78716c;
    font-size: 0.76rem;
    line-height: 1.2;
    margin: 0;
}}

.psm-kpi-sub {{
    color: #78716c;
    font-size: 0.72rem;
    line-height: 1.2;
    margin-top: 0.02rem;
    min-height: 1.0rem;
}}

.psm-kpi-sub--empty {{
    color: transparent;
}}

.psm-kpi-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.22rem;
    margin-top: 0.22rem;
}}

.psm-kpi-badge {{
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--psm-border);
    border-radius: 999px;
    padding: 0.06rem 0.36rem;
    font-size: 0.64rem;
    line-height: 1.05;
    color: #57534e;
    background: #fafaf9;
}}

.psm-kpi-badge--warn {{
    border-color: rgba(255, 87, 34, 0.33);
    color: #9a3412;
    background: rgba(255, 87, 34, 0.08);
}}

.psm-kpi-value {{
    color: #1c1917;
    font-size: 1.15rem;
    font-weight: 700;
    line-height: 1.2;
    margin-top: 0.32rem;
}}

.psm-kpi-row-gap {{
    height: 0.78rem;
}}

.psm-page-eyebrow {{
    display: block;
    color: var(--psm-muted);
    font-size: 0.82rem;
    line-height: 1.45;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-top: 0 !important;
    margin-bottom: 0.2rem;
    padding-top: 0.18rem;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"]::before {{
    content: "PRICEY";
    display: block;
    color: var(--psm-accent);
    font-size: 1.20rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    line-height: 1.0;
    margin: 0.2rem 0.15rem 0.65rem 0.2rem;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {{
    border-bottom: none !important;
    box-shadow: none !important;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] + hr,
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ~ hr,
section[data-testid="stSidebar"] hr {{
    display: none !important;
    border: 0 !important;
    box-shadow: none !important;
    margin: 0 !important;
}}

section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] + div,
section[data-testid="stSidebar"]
div[data-testid="stSidebarNav"] ~ div[data-testid="stHorizontalBlock"] {{
    border-top: none !important;
    box-shadow: none !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
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

.psm-step-card {{
    min-height: 7.1rem;
    padding: 0.25rem 0.05rem 0.15rem 0.05rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.35rem;
}}

.psm-muted {{
    color: var(--psm-muted);
    font-size: 0.92rem;
}}

.psm-context-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.6rem;
    width: 100%;
}}

.psm-context-chip {{
    background: transparent;
    border: 1px solid var(--psm-border);
    border-radius: 10px;
    padding: 0.45rem 0.65rem;
}}

.psm-context-banner {{
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 0.2rem 0.05rem 0.72rem 0.05rem;
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

.psm-notice {{
    border-radius: 10px;
    background: #f5f5f4;
    color: #1c1917;
    font-size: 0.95rem;
    line-height: 1.35;
    padding: 0.8rem 0.95rem;
    margin: 0.2rem 0 0.85rem 0;
}}

.psm-notice--negative {{
    border: 1px solid rgba(255, 87, 34, 0.33);
    color: var(--psm-accent);
}}

.psm-notice--negative strong {{
    color: var(--psm-accent);
}}

.psm-notice--positive {{
    border: 1px solid rgba(22, 163, 74, 0.38);
    color: #166534;
}}

.psm-notice--positive strong {{
    color: var(--psm-positive);
}}

div[data-testid="stPageLink"] > a {{
    border: 0 !important;
    background: transparent !important;
    padding: 0.05rem 0.0rem !important;
    margin: 0 !important;
    border-radius: 0 !important;
    color: var(--psm-accent) !important;
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    text-decoration: none !important;
}}

div[data-testid="stPageLink"] > a:hover {{
    color: var(--psm-accent) !important;
    text-decoration: underline !important;
}}

div[data-testid="stPageLink"] {{
    margin-top: 0.15rem !important;
    margin-bottom: 0.15rem !important;
}}

section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 0.12rem !important;
    width: fit-content !important;
    max-width: 100% !important;
    border: 0 !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    background-image: none !important;
}}

section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
    border: 0 !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    background-image: none !important;
}}

section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]::before,
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]::after,
section[data-testid="stSidebar"]
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]::before,
section[data-testid="stSidebar"]
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]::after,
section[data-testid="stSidebar"] div[data-testid="stButton"],
section[data-testid="stSidebar"] div[data-testid="stButton"]::before,
section[data-testid="stSidebar"] div[data-testid="stButton"]::after {{
    border: 0 !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    background-image: none !important;
    content: none !important;
}}

section[data-testid="stSidebar"] button[kind] {{
    min-height: 1.02rem !important;
    height: 1.02rem !important;
    min-width: 1.9rem !important;
    padding: 0.0rem 0.12rem !important;
    border-radius: 0.34rem !important;
    font-size: 0.58rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}}

section[data-testid="stSidebar"] button[kind] > div {{
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: center !important;
}}

section[data-testid="stSidebar"] button[kind] *,
section[data-testid="stSidebar"] button[kind] span,
section[data-testid="stSidebar"] button[kind] div p {{
    font-size: 0.58rem !important;
    font-weight: 600 !important;
    line-height: 1.02 !important;
    text-align: center !important;
    white-space: nowrap !important;
    word-break: normal !important;
    overflow-wrap: normal !important;
    margin: 0 auto !important;
}}

div[data-testid="stPageLink"] {{
    display: none !important;
}}

div[data-testid="stElementContainer"]:has(> div[data-testid="stPageLink"]) {{
    display: none !important;
}}

body[data-psm-sidebar-collapsed="true"] div[data-testid="stPageLink"] {{
    display: block !important;
}}

body[data-psm-sidebar-collapsed="true"]
div[data-testid="stElementContainer"]:has(> div[data-testid="stPageLink"]) {{
    display: block !important;
}}

@media (max-width: 980px) {{
    .psm-context-grid {{
        grid-template-columns: 1fr;
    }}
}}
</style>
"""

DEFAULT_DESKTOP_MAX_WIDTH = 2800


def inject_base_styles(*, max_width: int = DEFAULT_DESKTOP_MAX_WIDTH) -> None:
    st.markdown(BASE_STYLE_TEMPLATE.format(max_width=max_width), unsafe_allow_html=True)
    st.html(
        """
        <script>
        (function() {
          const parentDoc = window.parent && window.parent.document;
          if (!parentDoc) return;

          function updateSidebarState() {
            const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');
            if (!sidebar || !parentDoc.body) return;

            const sidebarNav = sidebar.querySelector('div[data-testid="stSidebarNav"]');
            const navRect = sidebarNav ? sidebarNav.getBoundingClientRect() : null;
            const navStyle = sidebarNav ? window.getComputedStyle(sidebarNav) : null;
            const navVisible = Boolean(
              sidebarNav &&
              navRect &&
              navRect.width >= 120 &&
              navRect.height > 40 &&
              navStyle &&
              navStyle.display !== "none" &&
              navStyle.visibility !== "hidden"
            );
            const collapsed = !navVisible;

            parentDoc.body.setAttribute(
              "data-psm-sidebar-collapsed",
              collapsed ? "true" : "false"
            );

            const pageLinkBlocks = parentDoc.querySelectorAll('div[data-testid="stPageLink"]');
            pageLinkBlocks.forEach(function(block) {
              block.setAttribute("data-psm-quick-nav", "true");
              const container = block.closest('div[data-testid="stElementContainer"]');
              if (container) {
                container.setAttribute("data-psm-quick-nav-container", "true");
                container.style.display = collapsed ? "block" : "none";
              }
              block.style.display = collapsed ? "block" : "none";
            });

            const activeLanguageButton = sidebar.querySelector('button[kind="primary"]');
            const activeLanguage = (
              (activeLanguageButton && activeLanguageButton.textContent) || ""
            ).trim().toUpperCase();
            const deActive = activeLanguage === "DE";
            const navLinks = sidebar.querySelectorAll('div[data-testid="stSidebarNav"] a');
            navLinks.forEach(function(link) {
              const labelNode =
                link.querySelector('[data-testid="stSidebarNavLinkLabel"]') || link;
              const textTarget = labelNode.querySelector("p, span") || labelNode;
              const currentLabel = (textTarget.textContent || "").trim();
              if (!currentLabel) return;
              if (!textTarget.dataset.psmOriginalLabel) {
                textTarget.dataset.psmOriginalLabel = currentLabel;
              }
              const originalLabel = textTarget.dataset.psmOriginalLabel;
              const normalized = originalLabel.toLowerCase();
              if (normalized === "results") {
                textTarget.textContent = deActive ? "ergebnisse" : originalLabel;
              } else if (normalized === "knowledge") {
                textTarget.textContent = deActive ? "methodik" : originalLabel;
              }
            });
          }

          updateSidebarState();
          window.addEventListener("resize", updateSidebarState);
          parentDoc.addEventListener("click", function() {
            setTimeout(updateSidebarState, 40);
          });
          setInterval(updateSidebarState, 500);
        })();
        </script>
        """,
        width="content",
        unsafe_allow_javascript=True,
    )


def render_notice(message: str, *, tone: str = "negative") -> None:
    tone_normalized = "positive" if tone == "positive" else "negative"
    css_class = f"psm-notice psm-notice--{tone_normalized}"
    st.markdown(
        f"<div class='{css_class}'>{escape(message)}</div>",
        unsafe_allow_html=True,
    )
