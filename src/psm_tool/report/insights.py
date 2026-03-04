from __future__ import annotations

from typing import Any

KPI_GLOSSARY: dict[str, str] = {
    "PMI": "Lower bound of the acceptable price range (marginal inexpensiveness).",
    "OPP": "Price where 'too cheap' and 'too expensive' concerns are balanced.",
    "IDP": "Price where value-for-money and expensiveness perceptions are balanced.",
    "PME": "Upper bound of the acceptable price range (marginal expensiveness).",
    "Accepted Range": "Band between PMI and PME where price acceptance is highest.",
    "Price Stress": "Difference between OPP and IDP; signals upward or downward pricing pressure.",
}


def _fmt_price(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "n/a"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_kpi_explanations(kpis: dict[str, Any]) -> list[dict[str, str]]:
    rows = [
        {
            "label": "PMI",
            "value": _fmt_price(kpis.get("pmi")),
            "explanation": KPI_GLOSSARY["PMI"],
        },
        {
            "label": "OPP",
            "value": _fmt_price(kpis.get("opp")),
            "explanation": KPI_GLOSSARY["OPP"],
        },
        {
            "label": "IDP",
            "value": _fmt_price(kpis.get("idp")),
            "explanation": KPI_GLOSSARY["IDP"],
        },
        {
            "label": "PME",
            "value": _fmt_price(kpis.get("pme")),
            "explanation": KPI_GLOSSARY["PME"],
        },
        {
            "label": "Accepted Range",
            "value": f"{_fmt_price(kpis.get('pmi'))} - {_fmt_price(kpis.get('pme'))}",
            "explanation": KPI_GLOSSARY["Accepted Range"],
        },
        {
            "label": "Price Stress",
            "value": _fmt_price(kpis.get("price_stress")),
            "explanation": KPI_GLOSSARY["Price Stress"],
        },
    ]
    return rows


def build_psm_summary(
    kpis: dict[str, Any],
    currency: str,
    segment_label: str,
    nms_kpis: dict[str, Any] | None = None,
) -> list[str]:
    pmi = _to_float(kpis.get("pmi", 0.0))
    pme = _to_float(kpis.get("pme", 0.0))
    opp = _to_float(kpis.get("opp", 0.0))
    idp = _to_float(kpis.get("idp", 0.0))

    sentences: list[str] = [
        f"The accepted price range is between {pmi:.2f} and {pme:.2f} {currency}.",
        f"The optimal pricing point (OPP) is around {opp:.2f} {currency}.",
    ]

    stress = opp - idp
    stress_pct = (stress / idp) if idp > 0 else 0.0
    width_pct = ((pme - pmi) / idp) if idp > 0 else 0.0

    if stress_pct <= -0.05:
        stress_sentence = (
            f"For {segment_label}, stress is negative (OPP below IDP), "
            "which indicates downward pressure."
        )
    elif stress_pct >= 0.05:
        stress_sentence = (
            f"For {segment_label}, stress is positive (OPP above IDP), "
            "which indicates upward price headroom."
        )
    else:
        stress_sentence = (
            f"For {segment_label}, OPP and IDP are closely aligned, "
            "suggesting a balanced pricing position."
        )

    if width_pct < 0.10:
        stress_sentence += " The acceptable range is narrow, indicating high price sensitivity."
    elif width_pct > 0.60:
        stress_sentence += (
            " The acceptable range is wide, indicating heterogeneous willingness to pay."
        )
    sentences.append(stress_sentence)

    statuses = [
        kpis.get("pmi_status"),
        kpis.get("opp_status"),
        kpis.get("idp_status"),
        kpis.get("pme_status"),
    ]
    if any(status != "clean" for status in statuses):
        sentences.append(
            "Some intersections are not clean (closest/interval), so point estimates "
            "should be interpreted with caution."
        )

    if nms_kpis is not None:
        max_revenue_price = _fmt_price(nms_kpis.get("max_revenue_price"))
        max_trial_price = _fmt_price(nms_kpis.get("max_trial_price"))
        sentences.append(
            "The highest turnover is at "
            f"{max_revenue_price} {currency}, while the highest trial is at "
            f"{max_trial_price} {currency}."
        )

    return sentences
