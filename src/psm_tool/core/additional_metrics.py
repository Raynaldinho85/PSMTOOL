from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class MetricResult:
    key: str
    label: str
    lens: str
    is_stable: bool
    value: float | None
    diagnostic_value: float | None
    reason: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_clean(kpis: dict[str, Any], key: str) -> bool:
    return str(kpis.get(f"{key}_status", "closest")) == "clean"


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def compute_additional_metrics(
    *,
    kpis: dict[str, Any],
    max_turnover_price: float | None = None,
    unit_cost: float | None = None,
) -> dict[str, MetricResult]:
    pmi = _safe_float(kpis.get("pmi"))
    pme = _safe_float(kpis.get("pme"))
    idp = _safe_float(kpis.get("idp"))
    opp = _safe_float(kpis.get("opp"))
    turnover = _safe_float(max_turnover_price)
    cost = _safe_float(unit_cost)

    pmi_clean = _is_clean(kpis, "pmi")
    pme_clean = _is_clean(kpis, "pme")
    idp_clean = _is_clean(kpis, "idp")
    opp_clean = _is_clean(kpis, "opp")

    psi_diagnostic = None
    if pmi is not None and pme is not None and idp not in (None, 0.0):
        psi_diagnostic = (pme - pmi) / idp
    psi_stable = pmi_clean and pme_clean and idp_clean and idp is not None and idp > 0
    psi_reason = None if psi_stable else "Requires clean PMI/PME/IDP and IDP > 0."
    psi_value = psi_diagnostic if psi_stable else None

    symmetry_diagnostic = None
    if pmi is not None and pme is not None and idp is not None:
        left = idp - pmi
        right = pme - idp
        if left != 0:
            symmetry_diagnostic = right / left
    symmetry_stable = pmi_clean and pme_clean and idp_clean and symmetry_diagnostic is not None
    symmetry_reason = (
        None if symmetry_stable else "Requires clean PMI/IDP/PME and non-zero left span."
    )
    symmetry_value = symmetry_diagnostic if symmetry_stable else None

    revenue_eff_diagnostic = None
    if turnover is not None and opp is not None:
        revenue_eff_diagnostic = turnover - opp
    revenue_eff_stable = opp_clean and revenue_eff_diagnostic is not None
    revenue_eff_reason = None if revenue_eff_stable else "Requires clean OPP and turnover optimum."
    revenue_eff_value = revenue_eff_diagnostic if revenue_eff_stable else None

    feasibility_diagnostic = None
    if pmi is not None and pme is not None and cost is not None and pme > pmi:
        above = max(0.0, pme - max(pmi, cost))
        feasibility_diagnostic = (above / (pme - pmi)) * 100.0
    feasibility_stable = (
        pmi_clean and pme_clean and cost is not None and feasibility_diagnostic is not None
    )
    feasibility_reason = (
        None
        if feasibility_stable
        else "Requires clean PMI/PME, cost, and positive accepted-range span."
    )
    feasibility_value = feasibility_diagnostic if feasibility_stable else None

    metrics = {
        "price_sensitivity_index": MetricResult(
            key="price_sensitivity_index",
            label="Price Sensitivity Index",
            lens="Perception",
            is_stable=psi_stable,
            value=psi_value,
            diagnostic_value=psi_diagnostic,
            reason=psi_reason,
        ),
        "range_symmetry": MetricResult(
            key="range_symmetry",
            label="Range Symmetry",
            lens="Perception",
            is_stable=symmetry_stable,
            value=symmetry_value,
            diagnostic_value=symmetry_diagnostic,
            reason=symmetry_reason,
        ),
        "revenue_efficiency": MetricResult(
            key="revenue_efficiency",
            label="Revenue Efficiency",
            lens="Cross-layer: Perception vs Economics proxy",
            is_stable=revenue_eff_stable,
            value=revenue_eff_value,
            diagnostic_value=revenue_eff_diagnostic,
            reason=revenue_eff_reason,
        ),
        "profit_feasibility_zone": MetricResult(
            key="profit_feasibility_zone",
            label="Profit Feasibility Zone",
            lens="Cross-layer: Perception vs Economics proxy",
            is_stable=feasibility_stable,
            value=feasibility_value,
            diagnostic_value=feasibility_diagnostic,
            reason=feasibility_reason,
        ),
    }
    return metrics
