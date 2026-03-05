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

    @staticmethod
    def _bounds(result: IntersectionResult) -> tuple[float | None, float | None]:
        if result.status != "interval":
            return None, None
        return result.low, result.high

    def as_dict(self) -> dict[str, float | str]:
        pmi_low, pmi_high = self._bounds(self.pmi)
        opp_low, opp_high = self._bounds(self.opp)
        idp_low, idp_high = self._bounds(self.idp)
        pme_low, pme_high = self._bounds(self.pme)
        has_unstable = any(
            status != "clean"
            for status in (self.pmi.status, self.opp.status, self.idp.status, self.pme.status)
        )
        return {
            "pmi": self.pmi.value,
            "pmi_status": self.pmi.status,
            "pmi_low": pmi_low,
            "pmi_high": pmi_high,
            "opp": self.opp.value,
            "opp_status": self.opp.status,
            "opp_low": opp_low,
            "opp_high": opp_high,
            "idp": self.idp.value,
            "idp_status": self.idp.status,
            "idp_low": idp_low,
            "idp_high": idp_high,
            "pme": self.pme.value,
            "pme_status": self.pme.status,
            "pme_low": pme_low,
            "pme_high": pme_high,
            "accepted_low": self.accepted_low,
            "accepted_high": self.accepted_high,
            "price_stress": self.price_stress,
            "stress_flag": self.stress_flag,
            "has_unstable_intersections": has_unstable,
        }

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame([self.as_dict()])


def _stress_flag(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


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

    accepted_low = min(pmi.value, pme.value)
    accepted_high = max(pmi.value, pme.value)
    stress = float(opp.value - idp.value)

    return PSMKPIResult(
        pmi=pmi,
        opp=opp,
        idp=idp,
        pme=pme,
        accepted_low=float(accepted_low),
        accepted_high=float(accepted_high),
        price_stress=stress,
        stress_flag=_stress_flag(stress),
    )
