from __future__ import annotations

from psm_tool.ui.results_logic import (
    apply_economics_settings,
    apply_manual_defaults_on_enter,
    apply_manual_grid_settings,
    apply_tested_price_settings,
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


def test_apply_economics_settings_only_updates_when_submitted() -> None:
    enabled, unit_cost = apply_economics_settings(
        submitted=False,
        draft_enabled=True,
        draft_unit_cost=18.0,
        stored_enabled=False,
        stored_unit_cost=9.0,
    )

    assert enabled is False
    assert unit_cost == 9.0


def test_apply_economics_settings_commits_draft_values() -> None:
    enabled, unit_cost = apply_economics_settings(
        submitted=True,
        draft_enabled=True,
        draft_unit_cost=18.0,
        stored_enabled=False,
        stored_unit_cost=9.0,
    )

    assert enabled is True
    assert unit_cost == 18.0


def test_manual_max_from_opp_uses_double_opp_and_ceil_to_next_10() -> None:
    assert manual_max_from_opp(80.0) == 160.0
    assert manual_max_from_opp(80.1) == 170.0


def test_apply_manual_grid_settings_only_updates_when_submitted() -> None:
    manual_min, manual_max, manual_step = apply_manual_grid_settings(
        submitted=False,
        draft_min=10.0,
        draft_max=60.0,
        draft_step=2.5,
        stored_min=0.0,
        stored_max=50.0,
        stored_step=5.0,
    )

    assert manual_min == 0.0
    assert manual_max == 50.0
    assert manual_step == 5.0


def test_apply_manual_grid_settings_commits_draft_values() -> None:
    manual_min, manual_max, manual_step = apply_manual_grid_settings(
        submitted=True,
        draft_min=10.0,
        draft_max=60.0,
        draft_step=2.5,
        stored_min=0.0,
        stored_max=50.0,
        stored_step=5.0,
    )

    assert manual_min == 10.0
    assert manual_max == 60.0
    assert manual_step == 2.5


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


def test_apply_tested_price_settings_only_updates_when_submitted() -> None:
    applied_price, active = apply_tested_price_settings(
        submitted=False,
        raw_value="30",
        requested_active=True,
        stored_price=25.0,
        stored_active=False,
    )

    assert applied_price == 25.0
    assert active is False


def test_apply_tested_price_settings_commits_new_valid_price() -> None:
    applied_price, active = apply_tested_price_settings(
        submitted=True,
        raw_value="30.0",
        requested_active=False,
        stored_price=25.0,
        stored_active=False,
    )

    assert applied_price == 30.0
    assert active is True
