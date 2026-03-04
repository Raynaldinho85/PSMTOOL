from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go


@dataclass(slots=True)
class BrowserPreflightError(RuntimeError):
    message: str

    def __str__(self) -> str:
        return self.message


def _is_browser_error(error: Exception) -> bool:
    text = str(error).lower()
    keys = (
        "chrome",
        "chromium",
        "browser",
        "executable",
        "could not locate",
        "failed to start",
    )
    return any(key in text for key in keys)


def check_kaleido_browser() -> None:
    fig = go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 1])])
    try:
        fig.to_image(format="png")
    except Exception as exc:  # pragma: no cover - branch depends on local runtime
        if _is_browser_error(exc):
            raise BrowserPreflightError(
                "Static export requires Chrome/Chromium for Kaleido v1. "
                "Install Chrome/Chromium, or run "
                '`python -c "import plotly.io as pio; pio.get_chrome()"`, '
                "or set BROWSER_PATH if your browser is not auto-discovered."
            ) from exc
        raise


def figure_to_png_bytes(fig: go.Figure) -> bytes:
    return fig.to_image(format="png")
