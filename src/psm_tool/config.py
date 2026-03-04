from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv
from typing import Literal


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
class AppConfig:
    demo_mode: bool = getenv("DEMO_MODE", "false").lower() == "true"
    app_password: str | None = getenv("APP_PASSWORD") or None
    max_upload_mb: int = int(getenv("MAX_UPLOAD_MB", "25"))
    max_rows_demo: int = int(getenv("MAX_ROWS_DEMO", "5000"))
