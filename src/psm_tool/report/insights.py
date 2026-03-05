from __future__ import annotations

import math
from typing import Any

from psm_tool.report.wording_policy import (
    apply_wording_policy,
    can_recommend,
    competition_caveat_line,
)

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

TURNOVER_GLOSSARY: dict[str, str] = {
    "Max Turnover Price": "Price where turnover index reaches its maximum (index = 100).",
    "Max Turnover Index": "Normalized turnover score on a 0-100 scale.",
    "PI Source": "Source used for purchase intention curve (ladder or NMS trial fallback).",
}

PROFIT_GLOSSARY: dict[str, str] = {
    "Unit Cost": "Manually entered unit cost used only in this session.",
    "Max Profit Price": "Price where profit proxy is highest.",
    "Max Profit Index": "Normalized profit proxy score on a 0-100 scale.",
    "Break-even (Cost)": "Price where unit margin is zero (price equals cost).",
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


def describe_turnover_source(source: str | None) -> tuple[str, str]:
    if source == "ladder":
        return (
            "PI ladder",
            "Uses explicit purchase-intention values from a provided price ladder table.",
        )
    return (
        "NMS trial fallback",
        (
            "Uses the modeled NMS trial curve from respondent anchor points "
            "when no explicit price ladder is provided."
        ),
    )


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
    product_label: str | None = None,
    nms_kpis: dict[str, Any] | None = None,
) -> list[str]:
    pmi = _to_float(kpis.get("pmi", 0.0))
    pme = _to_float(kpis.get("pme", 0.0))
    opp = _to_float(kpis.get("opp", 0.0))
    idp = _to_float(kpis.get("idp", 0.0))

    del nms_kpis  # PSM summary intentionally excludes PI/turnover statements.

    product_clean = (product_label or "").strip()
    country_clean = (segment_label or "").strip()
    if product_clean and country_clean:
        accepted_prefix = f"The accepted price range (for {product_clean} in {country_clean})"
    else:
        accepted_prefix = "The accepted price range"

    statuses = {
        "pmi": str(kpis.get("pmi_status", "closest")),
        "opp": str(kpis.get("opp_status", "closest")),
        "idp": str(kpis.get("idp_status", "closest")),
        "pme": str(kpis.get("pme_status", "closest")),
    }
    recommendation_allowed = can_recommend(statuses, allow_interval=False)
    unstable = any(status != "clean" for status in statuses.values())

    sentences: list[str] = [
        f"{accepted_prefix} is between {pmi:.2f} {currency} (PMI) and {pme:.2f} {currency} (PME).",
    ]
    if recommendation_allowed:
        sentences.append(f"The optimal pricing point (OPP) is around {opp:.2f} {currency}.")
    else:
        sentences.append(
            "OPP is not used for a target-price recommendation because intersection quality is not clean."
        )

    stress = opp - idp
    stress_pct = (stress / idp) if idp > 0 else 0.0
    width_pct = ((pme - pmi) / idp) if idp > 0 else 0.0

    if stress_pct <= -0.05:
        stress_sentence = (
            "Price stress is negative, because IDP is higher than OPP, "
            "which indicates downward pressure."
        )
    elif stress_pct >= 0.05:
        stress_sentence = (
            "Price stress is positive, because OPP is higher than IDP, "
            "which indicates upward price headroom."
        )
    else:
        stress_sentence = (
            "Price stress is neutral, because OPP equals IDP, "
            "which indicates a balanced pricing position."
        )

    if width_pct < 0.10:
        stress_sentence += " The acceptable range is narrow, indicating high price sensitivity."
    elif width_pct > 0.60:
        stress_sentence += (
            " The acceptable range is wide, indicating heterogeneous willingness to pay."
        )
    sentences.append(stress_sentence)

    if unstable:
        sentences.append(
            "Some intersections are not clean (closest/interval), so point estimates "
            "should be interpreted with caution."
        )

    sentences.append(
        f"The Indifference Price Point of {idp:.2f} {currency} (IDP) marks the perceived "
        "price balance where cheap and expensive perceptions are equal."
    )

    policy_applied = [
        apply_wording_policy(
            sentence,
            lens="Perception",
            status_flags={
                "unstable": unstable,
                "recommendation_blocked": (not recommendation_allowed and idx == 1),
            },
        )
        for idx, sentence in enumerate(sentences)
    ]
    policy_applied.append(competition_caveat_line())
    return policy_applied


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
        f"The highest modeled revenue is at {max_revenue_text} {currency}.",
        "NMS trial and revenue are modeled demand proxies, not observed demand.",
    ]

    if max_trial_text != "n/a" and max_revenue_text != "n/a":
        delta = max_revenue_price - max_trial_price
        if abs(delta) < 1e-9:
            sentences.append("Trial and revenue peaks align at the same price level.")
        elif delta > 0:
            sentences.append(
                "Revenue peaks at a higher price than trial, indicating a monetization trade-off."
            )
        else:
            sentences.append(
                "Revenue peaks at a lower price than trial, indicating earlier pricing maximizes "
                "the model output."
            )

    included_n = _read_nms_field(nms_result, "included_n")
    base_n = _read_nms_field(nms_result, "base_n")
    if included_n is not None and base_n is not None:
        sentences.append(
            f"NMS uses {included_n} of {base_n} respondents after eligibility "
            "and completeness checks."
        )

    if not bool(_read_nms_field(nms_result, "weighting_applied", False)):
        sentences.append(
            "NMS used an unweighted fallback because valid weights were not available."
        )

    filter_note = _read_nms_field(nms_result, "filter_note")
    if filter_note:
        sentences.append(str(filter_note))

    if segment_label:
        sentences.append(f"Context: {segment_label}.")

    policy_applied = [
        apply_wording_policy(sentence, lens="Modeled demand") for sentence in sentences
    ]
    policy_applied.append(competition_caveat_line())
    return policy_applied


def build_turnover_explanations(
    turnover_result: Any,
    *,
    currency: str,
    source: str | None,
) -> list[dict[str, str]]:
    source_label, source_note = describe_turnover_source(source)
    return [
        {
            "label": "Max Turnover Price",
            "value": (
                f"{_fmt_price(getattr(turnover_result, 'max_turnover_price', None))} {currency}"
            ),
            "explanation": TURNOVER_GLOSSARY["Max Turnover Price"],
        },
        {
            "label": "Max Turnover Index",
            "value": _fmt_price(getattr(turnover_result, "max_turnover_index", None)),
            "explanation": TURNOVER_GLOSSARY["Max Turnover Index"],
        },
        {
            "label": "PI Source",
            "value": source_label,
            "explanation": f"{TURNOVER_GLOSSARY['PI Source']} {source_note}",
        },
    ]


def build_turnover_summary(
    turnover_result: Any,
    *,
    currency: str,
    segment_label: str,
    source: str | None,
    kpi_statuses: dict[str, str] | None = None,
) -> list[str]:
    max_price = _fmt_price(getattr(turnover_result, "max_turnover_price", None))
    max_index = _fmt_price(getattr(turnover_result, "max_turnover_index", None))
    frame = getattr(turnover_result, "df", None)
    recommendation_allowed = (
        can_recommend(kpi_statuses, allow_interval=False) if kpi_statuses else True
    )
    unstable = not recommendation_allowed

    if recommendation_allowed:
        sentences = [
            f"The highest turnover can be achieved by setting the price at {max_price} {currency}.",
            f"At this point, the turnover index reaches {max_index} on the 0-100 scale.",
        ]
    else:
        sentences = [
            "Turnover optimization is not used for a target-price recommendation because required PSM intersections are not clean.",
            f"The current turnover index diagnostic value is {max_index}.",
        ]
    if frame is not None and hasattr(frame, "sort_values"):
        sorted_frame = frame.sort_values("price").reset_index(drop=True)
        if len(sorted_frame) > 1:
            pi_peak_idx = int(sorted_frame["purchase_intention_pct"].astype(float).idxmax())
            pi_peak_price = float(sorted_frame.loc[pi_peak_idx, "price"])
            max_turnover_price = float(getattr(turnover_result, "max_turnover_price", 0.0))
            if max_turnover_price > pi_peak_price:
                sentences.append(
                    "The turnover peak sits above the PI peak, indicating monetization favors "
                    "a higher price than pure intent."
                )
            elif max_turnover_price < pi_peak_price:
                sentences.append(
                    "The turnover peak sits below the PI peak, indicating turnover is optimized "
                    "before intent reaches its maximum."
                )
            else:
                sentences.append("PI and turnover peak at the same price level in this view.")
    source_label, _source_note = describe_turnover_source(source)
    sentences.append(f"PI source in this chart: {source_label}.")
    if segment_label:
        sentences.append(f"Context: {segment_label}.")

    policy_applied = [
        apply_wording_policy(
            sentence,
            lens="Economics proxy",
            status_flags={"unstable": unstable, "recommendation_blocked": not recommendation_allowed},
        )
        for sentence in sentences
    ]
    policy_applied.append(competition_caveat_line())
    return policy_applied


def build_profit_explanations(profit_result: Any, *, currency: str) -> list[dict[str, str]]:
    unit_cost = _fmt_price(getattr(profit_result, "unit_cost", None))
    max_price = _fmt_price(getattr(profit_result, "max_profit_price", None))
    max_index = _fmt_price(getattr(profit_result, "max_profit_index", None))
    return [
        {
            "label": "Unit Cost",
            "value": f"{unit_cost} {currency}",
            "explanation": PROFIT_GLOSSARY["Unit Cost"],
        },
        {
            "label": "Max Profit Price",
            "value": f"{max_price} {currency}",
            "explanation": PROFIT_GLOSSARY["Max Profit Price"],
        },
        {
            "label": "Max Profit Index",
            "value": max_index,
            "explanation": PROFIT_GLOSSARY["Max Profit Index"],
        },
        {
            "label": "Break-even (Cost)",
            "value": f"{unit_cost} {currency}",
            "explanation": PROFIT_GLOSSARY["Break-even (Cost)"],
        },
    ]


def build_profit_summary(
    profit_result: Any,
    *,
    currency: str,
    segment_label: str,
    product_label: str | None = None,
    kpi_statuses: dict[str, str] | None = None,
) -> list[str]:
    unit_cost = _fmt_price(getattr(profit_result, "unit_cost", None))
    max_price = _fmt_price(getattr(profit_result, "max_profit_price", None))
    max_index = _fmt_price(getattr(profit_result, "max_profit_index", None))
    unit_cost_num = _to_float(getattr(profit_result, "unit_cost", None), default=float("nan"))
    max_price_num = _to_float(
        getattr(profit_result, "max_profit_price", None), default=float("nan")
    )

    product_clean = (product_label or "").strip()
    segment_clean = (segment_label or "").strip()
    if product_clean and segment_clean:
        break_even_context = f"For {product_clean} in {segment_clean}, "
    elif product_clean:
        break_even_context = f"For {product_clean}, "
    elif segment_clean:
        break_even_context = f"For {segment_clean}, "
    else:
        break_even_context = ""

    recommendation_allowed = (
        can_recommend(kpi_statuses, allow_interval=False) if kpi_statuses else True
    )
    unstable = not recommendation_allowed
    if recommendation_allowed:
        sentences = [
            (
                f"Given unit cost {unit_cost} {currency}, the highest profit proxy is achieved "
                f"at {max_price} {currency}."
            ),
            f"At this point, the profit index reaches {max_index} on the 0-100 scale.",
            f"{break_even_context}the break-even marker is set at {unit_cost} {currency}.",
        ]
    else:
        sentences = [
            "Profit optimization is not used for a target-price recommendation because required PSM intersections are not clean.",
            f"{break_even_context}the break-even marker is set at {unit_cost} {currency}.",
        ]
    if math.isfinite(unit_cost_num) and math.isfinite(max_price_num):
        delta = max_price_num - unit_cost_num
        if delta > 0:
            sentences.append(
                "The maximum-profit price sits above break-even, indicating positive unit margin "
                "at the optimum."
            )
        elif delta < 0:
            sentences.append(
                "The maximum-profit price sits below break-even, indicating the current setup "
                "does not reach positive unit margin at the optimum."
            )
        else:
            sentences.append(
                "The maximum-profit price equals break-even, indicating a zero unit margin "
                "at the optimum."
            )
    if segment_label:
        sentences.append(f"Context: {segment_label}.")
    policy_applied = [
        apply_wording_policy(
            sentence,
            lens="Economics proxy",
            status_flags={"unstable": unstable, "recommendation_blocked": not recommendation_allowed},
        )
        for sentence in sentences
    ]
    policy_applied.append(competition_caveat_line())
    return policy_applied
