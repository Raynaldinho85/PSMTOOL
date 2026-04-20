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


def apply_economics_settings(
    *,
    submitted: bool,
    draft_enabled: bool,
    draft_unit_cost: float,
    stored_enabled: bool,
    stored_unit_cost: float,
) -> tuple[bool, float]:
    if not submitted:
        return bool(stored_enabled), float(stored_unit_cost)
    return bool(draft_enabled), max(0.0, float(draft_unit_cost))


def apply_manual_grid_settings(
    *,
    submitted: bool,
    draft_min: float,
    draft_max: float,
    draft_step: float,
    stored_min: float,
    stored_max: float,
    stored_step: float,
) -> tuple[float, float, float]:
    if not submitted:
        return float(stored_min), float(stored_max), float(stored_step)
    return float(draft_min), float(draft_max), float(draft_step)


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


def apply_tested_price_settings(
    *,
    submitted: bool,
    raw_value: object,
    requested_active: bool,
    stored_price: float | None,
    stored_active: bool,
) -> tuple[float | None, bool]:
    if not submitted:
        return stored_price, bool(stored_active)

    parsed_price = parse_tested_price(raw_value)
    active, applied_price = resolve_tested_price_activation(
        parsed_price=parsed_price,
        previous_valid_price=stored_price,
        requested_active=requested_active,
    )
    return applied_price, active


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
