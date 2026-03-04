from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from psm_tool.core.intersections import IntersectionResult, find_intersection


@dataclass(slots=True)
class PSMKPIResult:
    pmi: IntersectionResult
    opp: IntersectionResult
    idp: IntersectionResult
    pme: IntersectionResult
    accepted_low: float
    accepted_high: float
    price_stress: float
    stress_flag: str


def compute_psm_kpis(curves: pd.DataFrame) -> PSMKPIResult:
    prices = curves["price"].to_numpy(dtype=float)
    too_cheap = curves["too_cheap"].to_numpy(dtype=float)
    bargain = curves["bargain"].to_numpy(dtype=float)
    expensive = curves["expensive"].to_numpy(dtype=float)
    too_expensive = curves["too_expensive"].to_numpy(dtype=float)
    not_bargain = curves["not_bargain"].to_numpy(dtype=float)
    not_expensive = curves["not_expensive"].to_numpy(dtype=float)

    opp = find_intersection(prices, too_cheap, too_expensive)
    idp = find_intersection(prices, bargain, expensive)
    pmi = find_intersection(prices, too_cheap, not_bargain)
    pme = find_intersection(prices, too_expensive, not_expensive)
    stress = float(opp.value - idp.value)
    return PSMKPIResult(
        pmi=pmi,
        opp=opp,
        idp=idp,
        pme=pme,
        accepted_low=float(pmi.value),
        accepted_high=float(pme.value),
        price_stress=stress,
        stress_flag="positive" if stress > 0 else "negative" if stress < 0 else "neutral",
    )
