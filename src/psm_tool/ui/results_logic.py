from __future__ import annotations

import math


def ceil_to_next_10(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        return 0.0
    return float(math.ceil(value / 10.0) * 10.0)


def manual_max_from_opp(opp: float) -> float:
    return ceil_to_next_10(2.0 * float(opp))


def apply_manual_defaults_on_enter(
    *,
    mode: str,
    previous_mode: str,
    initialized: bool,
    manual_min: float,
    manual_max: float,
    opp: float,
) -> tuple[float, float, bool]:
    if mode == "manual" and previous_mode != "manual" and not initialized:
        return 0.0, manual_max_from_opp(opp), True
    return float(manual_min), float(manual_max), bool(initialized)
