from __future__ import annotations

from psm_tool.core.additional_metrics import compute_additional_metrics


def _base_kpis() -> dict[str, float | str]:
    return {
        "pmi": 10.0,
        "opp": 20.0,
        "idp": 25.0,
        "pme": 40.0,
        "pmi_status": "clean",
        "opp_status": "clean",
        "idp_status": "clean",
        "pme_status": "clean",
    }


def test_additional_metrics_compute_when_required_inputs_are_clean() -> None:
    metrics = compute_additional_metrics(
        kpis=_base_kpis(),
        max_turnover_price=24.0,
        unit_cost=22.0,
    )

    assert metrics["price_sensitivity_index"].is_stable is True
    assert metrics["price_sensitivity_index"].value == 1.2
    assert metrics["range_symmetry"].is_stable is True
    assert metrics["range_symmetry"].value == 1.0
    assert metrics["revenue_efficiency"].is_stable is True
    assert metrics["revenue_efficiency"].value == 4.0
    assert metrics["profit_feasibility_zone"].is_stable is True
    assert metrics["profit_feasibility_zone"].value == 60.0


def test_additional_metrics_mark_unstable_when_status_not_clean() -> None:
    kpis = _base_kpis()
    kpis["idp_status"] = "interval"
    kpis["opp_status"] = "closest"
    metrics = compute_additional_metrics(kpis=kpis, max_turnover_price=24.0, unit_cost=22.0)

    assert metrics["price_sensitivity_index"].is_stable is False
    assert metrics["price_sensitivity_index"].value is None
    assert metrics["price_sensitivity_index"].diagnostic_value == 1.2

    assert metrics["range_symmetry"].is_stable is False
    assert metrics["range_symmetry"].value is None
    assert metrics["range_symmetry"].diagnostic_value == 1.0

    assert metrics["revenue_efficiency"].is_stable is False
    assert metrics["revenue_efficiency"].value is None
    assert metrics["revenue_efficiency"].diagnostic_value == 4.0


def test_profit_feasibility_zone_requires_cost() -> None:
    metrics = compute_additional_metrics(kpis=_base_kpis(), max_turnover_price=24.0, unit_cost=None)

    assert metrics["profit_feasibility_zone"].is_stable is False
    assert metrics["profit_feasibility_zone"].value is None
    assert metrics["profit_feasibility_zone"].diagnostic_value is None
    assert metrics["profit_feasibility_zone"].reason is not None
