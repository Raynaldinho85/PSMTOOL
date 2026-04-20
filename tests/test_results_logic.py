from __future__ import annotations

from psm_tool.ui.results_logic import (
    apply_manual_defaults_on_enter,
    ceil_to_next_10,
    manual_max_from_opp,
    parse_tested_price,
    resolve_tested_price_activation,
)


def test_ceil_to_next_10_rounding_examples() -> None:
    assert ceil_to_next_10(201.0) == 210.0
    assert ceil_to_next_10(210.0) == 210.0
    assert ceil_to_next_10(0.0) == 0.0


def test_manual_defaults_on_enter_manual_sets_min_zero_and_max_from_opp_exact_multiple() -> None:
    min_out, max_out, initialized = apply_manual_defaults_on_enter(
        mode="manual",
        previous_mode="auto",
        initialized=False,
        manual_min=12.0,
        manual_max=34.0,
        opp=105.0,
    )
    assert min_out == 0.0
    assert max_out == 210.0
    assert initialized is True


def test_manual_defaults_on_enter_manual_sets_min_zero_and_max_from_opp_non_multiple() -> None:
    min_out, max_out, initialized = apply_manual_defaults_on_enter(
        mode="manual",
        previous_mode="auto",
        initialized=False,
        manual_min=12.0,
        manual_max=34.0,
        opp=100.5,
    )
    assert min_out == 0.0
    assert max_out == 210.0
    assert initialized is True


def test_manual_user_edits_persist_across_mode_toggle_after_initialization() -> None:
    min_out, max_out, initialized = apply_manual_defaults_on_enter(
        mode="manual",
        previous_mode="auto",
        initialized=True,
        manual_min=7.0,
        manual_max=333.0,
        opp=80.0,
    )
    assert min_out == 7.0
    assert max_out == 333.0
    assert initialized is True


def test_manual_max_from_opp_uses_double_opp_and_ceil_to_next_10() -> None:
    assert manual_max_from_opp(80.0) == 160.0
    assert manual_max_from_opp(80.1) == 170.0


def test_parse_tested_price_requires_positive_finite_numeric_value() -> None:
    assert parse_tested_price("12.5") == 12.5
    assert parse_tested_price("") is None
    assert parse_tested_price("abc") is None
    assert parse_tested_price("0") is None
    assert parse_tested_price("-1") is None
    assert parse_tested_price("nan") is None
    assert parse_tested_price("inf") is None


def test_tested_price_auto_activates_when_new_valid_value_is_entered() -> None:
    active, stored = resolve_tested_price_activation(
        parsed_price=25.0,
        previous_valid_price=None,
        requested_active=False,
    )

    assert active is True
    assert stored == 25.0


def test_tested_price_can_be_manually_deactivated_after_auto_activation() -> None:
    active, stored = resolve_tested_price_activation(
        parsed_price=25.0,
        previous_valid_price=25.0,
        requested_active=False,
    )

    assert active is False
    assert stored == 25.0


def test_tested_price_invalid_value_forces_inactive() -> None:
    active, stored = resolve_tested_price_activation(
        parsed_price=None,
        previous_valid_price=25.0,
        requested_active=True,
    )

    assert active is False
    assert stored is None
