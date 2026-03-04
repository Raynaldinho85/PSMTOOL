from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv
from typing import Literal


def _env_bool(name: str, default: bool) -> bool:
    raw = getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class GridConfig:
    mode: Literal["auto", "manual"] = "auto"
    snap_enabled: bool = True
    currency_snap: dict[str, float] = field(
        default_factory=lambda: {"EUR": 5.0, "SEK": 20.0, "CHF": 5.0}
    )
    min_price: float | None = None
    max_price: float | None = None
    step: float | None = None


@dataclass(slots=True)
class PIConfig:
    enabled: bool = True
    puki_threshold: Literal[2, 3] = 2
    population: Literal["psm_valid_only"] = "psm_valid_only"


@dataclass(slots=True)
class OutlierConfig:
    enabled: bool = False
    method: Literal["quantile"] = "quantile"
    level: Literal["mild", "medium", "strict"] = "medium"


@dataclass(slots=True)
class AppConfig:
    demo_mode: bool = field(default_factory=lambda: _env_bool("DEMO_MODE", default=False))
    app_password: str | None = field(default_factory=lambda: getenv("APP_PASSWORD") or None)
    max_upload_mb: int = field(default_factory=lambda: int(getenv("MAX_UPLOAD_MB", "25")))
    max_rows_demo: int = field(default_factory=lambda: int(getenv("MAX_ROWS_DEMO", "5000")))
