from __future__ import annotations

import plotly.graph_objects as go

from psm_tool.i18n.runtime import tr
from psm_tool.plots.style import apply_white_chart_theme

BROWSER_GUIDANCE = (
    "Static export requires Chrome/Chromium for Kaleido v1. "
    "Install Chrome/Chromium, or run "
    '`python -c "import plotly.io as pio; pio.get_chrome()"`, '
    "or set BROWSER_PATH if the browser is installed but not auto-discovered."
)


class BrowserPreflightError(RuntimeError):
    """Raised when static export dependencies are not available."""


STATIC_EXPORT_MARGIN_MINIMUMS = {"l": 70, "r": 70, "t": 120, "b": 40}


def _is_browser_error(error: Exception) -> bool:
    text = str(error).lower()
    tokens = (
        "chrome",
        "chromium",
        "browser",
        "could not locate",
        "executable",
        "failed to start",
        "permission denied",
        "access is denied",
    )
    return any(token in text for token in tokens)


def check_kaleido_browser(language: str | None = None) -> None:
    probe = go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 1], mode="lines")])
    try:
        probe.to_image(format="png")
    except Exception as exc:  # pragma: no cover - depends on local runtime environment
        if _is_browser_error(exc):
            raise BrowserPreflightError(tr(BROWSER_GUIDANCE, language)) from exc
        raise


def _apply_static_safe_margins(fig: go.Figure) -> None:
    current = fig.layout.margin
    margin_values = {
        "l": current.l if current and current.l is not None else 0,
        "r": current.r if current and current.r is not None else 0,
        "t": current.t if current and current.t is not None else 0,
        "b": current.b if current and current.b is not None else 0,
    }
    fig.update_layout(
        margin={
            side: max(int(value), STATIC_EXPORT_MARGIN_MINIMUMS[side])
            for side, value in margin_values.items()
        }
    )


def prepare_figure_for_static_export(
    fig: go.Figure,
    *,
    safe_margins: bool = True,
) -> go.Figure:
    prepared = apply_white_chart_theme(go.Figure(fig))
    if safe_margins:
        _apply_static_safe_margins(prepared)
    return prepared


def figure_to_png_bytes(fig: go.Figure, *, safe_margins: bool = True) -> bytes:
    themed = prepare_figure_for_static_export(fig, safe_margins=safe_margins)
    return themed.to_image(format="png")
