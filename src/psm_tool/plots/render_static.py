from __future__ import annotations

import plotly.graph_objects as go

BROWSER_GUIDANCE = (
    "Static export requires Chrome/Chromium for Kaleido v1. "
    "Install Chrome/Chromium, or run "
    '`python -c "import plotly.io as pio; pio.get_chrome()"`, '
    "or set BROWSER_PATH if the browser is installed but not auto-discovered."
)


class BrowserPreflightError(RuntimeError):
    """Raised when static export dependencies are not available."""


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


def check_kaleido_browser() -> None:
    probe = go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 1], mode="lines")])
    try:
        probe.to_image(format="png")
    except Exception as exc:  # pragma: no cover - depends on local runtime environment
        if _is_browser_error(exc):
            raise BrowserPreflightError(BROWSER_GUIDANCE) from exc
        raise


def figure_to_png_bytes(fig: go.Figure) -> bytes:
    return fig.to_image(format="png")
