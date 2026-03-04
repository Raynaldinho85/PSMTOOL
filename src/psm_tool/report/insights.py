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

NMS_GLOSSARY: dict[str, str] = {
    "Max Trial Price": "Price where modeled trial intent reaches its maximum.",
    "Max Revenue Price": "Price where modeled revenue per 100 prospects reaches its maximum.",
    "Included N": (
        "Respondents included in NMS after PI/PUKI eligibility and missing-value handling."
    ),
    "PUKI Filter": "Eligibility threshold used for PI population selection.",
    "Weighting": "Whether valid survey weights were applied in NMS averaging.",
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


def _read_nms_field(nms_result: Any, field: str, default: Any = None) -> Any:
    if isinstance(nms_result, dict):
        return nms_result.get(field, default)
    return getattr(nms_result, field, default)


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


def build_nms_explanations(nms_result: Any, currency: str) -> list[dict[str, str]]:
    max_trial_price = _fmt_price(_read_nms_field(nms_result, "max_trial_price"))
    max_revenue_price = _fmt_price(_read_nms_field(nms_result, "max_revenue_price"))
    included_n = _read_nms_field(nms_result, "included_n", "n/a")
    puki_filter_applied = bool(_read_nms_field(nms_result, "puki_filter_applied", False))
    puki_threshold = _read_nms_field(nms_result, "puki_threshold")
    weighting_applied = bool(_read_nms_field(nms_result, "weighting_applied", False))

    if puki_filter_applied and puki_threshold is not None:
        puki_value = f"<= {puki_threshold}"
    elif puki_filter_applied:
        puki_value = "Applied"
    else:
        puki_value = "Not applied"

    weighting_value = "Weighted" if weighting_applied else "Unweighted fallback"

    return [
        {
            "label": "Max Trial Price",
            "value": f"{max_trial_price} {currency}",
            "explanation": NMS_GLOSSARY["Max Trial Price"],
        },
        {
            "label": "Max Revenue Price",
            "value": f"{max_revenue_price} {currency}",
            "explanation": NMS_GLOSSARY["Max Revenue Price"],
        },
        {
            "label": "Included N",
            "value": str(included_n),
            "explanation": NMS_GLOSSARY["Included N"],
        },
        {
            "label": "PUKI Filter",
            "value": puki_value,
            "explanation": NMS_GLOSSARY["PUKI Filter"],
        },
        {
            "label": "Weighting",
            "value": weighting_value,
            "explanation": NMS_GLOSSARY["Weighting"],
        },
    ]


def build_nms_summary(
    nms_result: Any,
    currency: str,
    segment_label: str,
) -> list[str]:
    max_trial_price = _to_float(
        _read_nms_field(nms_result, "max_trial_price"), default=float("nan")
    )
    max_revenue_price = _to_float(
        _read_nms_field(nms_result, "max_revenue_price"), default=float("nan")
    )
    max_trial_text = _fmt_price(max_trial_price)
    max_revenue_text = _fmt_price(max_revenue_price)

    sentences = [
        f"The highest trial is at {max_trial_text} {currency}.",
        f"The highest turnover is at {max_revenue_text} {currency}.",
    ]

    if max_trial_text != "n/a" and max_revenue_text != "n/a":
        delta = max_revenue_price - max_trial_price
        if abs(delta) < 1e-9:
            sentences.append(
                f"For {segment_label}, trial and turnover peaks align at the same price level."
            )
        elif delta > 0:
            sentences.append(
                f"For {segment_label}, turnover peaks at a higher price than trial, indicating "
                "upward monetization potential."
            )
        else:
            sentences.append(
                f"For {segment_label}, turnover peaks at a lower price than trial, indicating "
                "volume gains require earlier pricing."
            )

    included_n = _read_nms_field(nms_result, "included_n")
    base_n = _read_nms_field(nms_result, "base_n")
    if included_n is not None and base_n is not None:
        sentences.append(
            f"NMS uses {included_n} of {base_n} respondents after eligibility and "
            "completeness checks."
        )

    if not bool(_read_nms_field(nms_result, "weighting_applied", False)):
        sentences.append(
            "NMS used an unweighted fallback because valid weights were not available."
        )

    filter_note = _read_nms_field(nms_result, "filter_note")
    if filter_note:
        sentences.append(str(filter_note))

    return sentences
