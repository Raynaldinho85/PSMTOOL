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


def parse_tested_price(raw_value: object) -> float | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value) or value <= 0.0:
        return None
    return value


def resolve_tested_price_activation(
    *,
    parsed_price: float | None,
    previous_valid_price: float | None,
    requested_active: bool,
) -> tuple[bool, float | None]:
    if parsed_price is None:
        return False, None
    if previous_valid_price is None or not math.isclose(
        float(parsed_price),
        float(previous_valid_price),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        return True, float(parsed_price)
    return bool(requested_active), float(parsed_price)
