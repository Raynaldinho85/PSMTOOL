from __future__ import annotations

import math
from typing import Any

from psm_tool.i18n.runtime import normalize_language, tr
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


def _pick_text(selected_language: str, de_text: str, en_text: str) -> str:
    return de_text if selected_language == "de" else en_text


def _format_price_with_status(
    kpis: dict[str, Any],
    *,
    key: str,
    currency: str,
) -> str:
    status = str(kpis.get(f"{key}_status", "closest"))
    value = _to_float(kpis.get(key), default=float("nan"))
    if status == "clean":
        return f"{value:.2f} {currency}"
    if status == "interval":
        low = kpis.get(f"{key}_low")
        high = kpis.get(f"{key}_high")
        if low is not None and high is not None:
            return f"[{float(low):.2f}, {float(high):.2f}] {currency} (~ {value:.2f} {currency})"
        return f"{value:.2f} {currency} (~mid)"
    return f"{value:.2f} {currency} (diagnostic)"


def _non_clean_status_note(
    kpi_statuses: dict[str, str] | None,
    language: str | None = None,
) -> str | None:
    if not kpi_statuses:
        return None
    non_clean = [
        f"{key.upper()}={value}" for key, value in kpi_statuses.items() if value != "clean"
    ]
    if not non_clean:
        return None
    return tr(
        "Intersection status: {statuses}.",
        language,
        statuses=", ".join(non_clean),
    )


def describe_turnover_source(source: str | None, language: str | None = None) -> tuple[str, str]:
    if source == "ladder":
        return (
            tr("PI ladder", language),
            tr(
                "Uses explicit purchase-intention values from a provided price ladder table.",
                language,
            ),
        )
    return (
        tr("NMS trial fallback", language),
        tr(
            (
                "Uses the modeled NMS trial curve from respondent anchor points "
                "when no explicit price ladder is provided."
            ),
            language,
        ),
    )


def build_kpi_explanations(
    kpis: dict[str, Any],
    language: str | None = None,
) -> list[dict[str, str]]:
    rows = [
        {
            "label": tr("PMI", language),
            "value": _fmt_price(kpis.get("pmi")),
            "explanation": tr(KPI_GLOSSARY["PMI"], language),
        },
        {
            "label": tr("OPP", language),
            "value": _fmt_price(kpis.get("opp")),
            "explanation": tr(KPI_GLOSSARY["OPP"], language),
        },
        {
            "label": tr("IDP", language),
            "value": _fmt_price(kpis.get("idp")),
            "explanation": tr(KPI_GLOSSARY["IDP"], language),
        },
        {
            "label": tr("PME", language),
            "value": _fmt_price(kpis.get("pme")),
            "explanation": tr(KPI_GLOSSARY["PME"], language),
        },
        {
            "label": tr("Accepted Range", language),
            "value": f"{_fmt_price(kpis.get('pmi'))} - {_fmt_price(kpis.get('pme'))}",
            "explanation": tr(KPI_GLOSSARY["Accepted Range"], language),
        },
        {
            "label": tr("Price Stress", language),
            "value": _fmt_price(kpis.get("price_stress")),
            "explanation": tr(KPI_GLOSSARY["Price Stress"], language),
        },
    ]
    return rows


def build_psm_summary(
    kpis: dict[str, Any],
    currency: str,
    segment_label: str,
    product_label: str | None = None,
    nms_kpis: dict[str, Any] | None = None,
    language: str | None = None,
) -> list[str]:
    selected_language = normalize_language(language)
    pmi = _to_float(kpis.get("pmi", 0.0))
    pme = _to_float(kpis.get("pme", 0.0))
    opp = _to_float(kpis.get("opp", 0.0))
    idp = _to_float(kpis.get("idp", 0.0))

    del nms_kpis  # PSM summary intentionally excludes PI/turnover statements.

    product_clean = (product_label or "").strip()
    country_clean = (segment_label or "").strip()
    if product_clean and country_clean:
        accepted_prefix = (
            f"Der akzeptierte Preisbereich (für {product_clean} in {country_clean})"
            if selected_language == "de"
            else f"The accepted price range (for {product_clean} in {country_clean})"
        )
    else:
        accepted_prefix = (
            "Der akzeptierte Preisbereich"
            if selected_language == "de"
            else "The accepted price range"
        )

    statuses = {
        "pmi": str(kpis.get("pmi_status", "closest")),
        "opp": str(kpis.get("opp_status", "closest")),
        "idp": str(kpis.get("idp_status", "closest")),
        "pme": str(kpis.get("pme_status", "closest")),
    }
    pmi_clean = statuses["pmi"] == "clean"
    pme_clean = statuses["pme"] == "clean"
    opp_clean = statuses["opp"] == "clean"
    idp_clean = statuses["idp"] == "clean"
    recommendation_allowed = can_recommend(statuses, allow_interval=False)
    unstable = any(status != "clean" for status in statuses.values())

    pmi_text = _format_price_with_status(kpis, key="pmi", currency=currency)
    pme_text = _format_price_with_status(kpis, key="pme", currency=currency)
    opp_text = _format_price_with_status(kpis, key="opp", currency=currency)
    idp_text = _format_price_with_status(kpis, key="idp", currency=currency)

    sentences: list[str] = [
        _pick_text(
            selected_language,
            f"{accepted_prefix} liegt zwischen {pmi_text} (PMI) und {pme_text} (PME).",
            f"{accepted_prefix} is between {pmi_text} (PMI) and {pme_text} (PME).",
        )
    ]
    if recommendation_allowed:
        sentences.append(
            _pick_text(
                selected_language,
                f"Der optimale Preispunkt (OPP) liegt bei etwa {opp_text}.",
                f"The optimal pricing point (OPP) is around {opp_text}.",
            )
        )
    else:
        sentences.append(
            _pick_text(
                selected_language,
                (
                    "OPP wird nicht für eine Zielpreisempfehlung verwendet, weil "
                    "die Schnittpunktqualität nicht clean ist."
                ),
                (
                    "OPP is not used for a target-price recommendation because "
                    "intersection quality is not clean."
                ),
            )
        )

    if opp_clean and idp_clean:
        stress = opp - idp
        stress_pct = (stress / idp) if idp > 0 else 0.0
        if stress_pct <= -0.05:
            stress_sentence = _pick_text(
                selected_language,
                (
                    "Price Stress ist negativ, weil IDP höher als OPP liegt; "
                    "das deutet auf Abwärtsdruck hin."
                ),
                (
                    "Price stress is negative, because IDP is higher than OPP, "
                    "which indicates downward pressure."
                ),
            )
        elif stress_pct >= 0.05:
            stress_sentence = _pick_text(
                selected_language,
                (
                    "Price Stress ist positiv, weil OPP höher als IDP liegt; "
                    "das deutet auf Preis-Spielraum nach oben hin."
                ),
                (
                    "Price stress is positive, because OPP is higher than IDP, "
                    "which indicates upward price headroom."
                ),
            )
        else:
            stress_sentence = _pick_text(
                selected_language,
                (
                    "Price Stress ist neutral, weil OPP und IDP übereinstimmen; "
                    "das deutet auf eine ausgewogene Preisposition hin."
                ),
                (
                    "Price stress is neutral, because OPP equals IDP, which "
                    "indicates a balanced pricing position."
                ),
            )
    else:
        stress_sentence = _pick_text(
            selected_language,
            (
                "Price Stress wird nur diagnostisch berichtet, weil die "
                "Schnittpunktqualität von OPP oder IDP nicht clean ist."
            ),
            (
                "Price stress is reported as diagnostic only because OPP or IDP "
                "intersection quality is not clean."
            ),
        )

    if pmi_clean and pme_clean and idp_clean:
        width_pct = ((pme - pmi) / idp) if idp > 0 else 0.0
        if width_pct < 0.10:
            stress_sentence += _pick_text(
                selected_language,
                " Der akzeptierte Bereich ist eng, was auf eine hohe Preissensitivität hinweist.",
                " The acceptable range is narrow, indicating high price sensitivity.",
            )
        elif width_pct > 0.60:
            stress_sentence += _pick_text(
                selected_language,
                (
                    " Der akzeptierte Bereich ist breit, was auf eine "
                    "heterogene Zahlungsbereitschaft hindeutet."
                ),
                (" The acceptable range is wide, indicating heterogeneous willingness to pay."),
            )
    else:
        stress_sentence += _pick_text(
            selected_language,
            " Die Einordnung der Bereichsbreite ist nur diagnostisch.",
            " Accepted-range width classification is diagnostic only.",
        )
    sentences.append(stress_sentence)

    if unstable:
        sentences.append(
            _pick_text(
                selected_language,
                (
                    "Einige Schnittpunkte sind nicht clean (closest/interval), "
                    "daher sollten Punktwerte mit Vorsicht interpretiert werden."
                ),
                (
                    "Some intersections are not clean (closest/interval), so "
                    "point estimates should be interpreted with caution."
                ),
            )
        )

    sentences.append(
        _pick_text(
            selected_language,
            (
                f"Der Indifference Price Point von {idp_text} (IDP) markiert "
                "das wahrgenommene Preisgleichgewicht, bei dem sich günstig- "
                "und teuer-Wahrnehmung ausgleichen."
            ),
            (
                f"The Indifference Price Point of {idp_text} (IDP) marks the "
                "perceived price balance where cheap and expensive perceptions "
                "are equal."
            ),
        )
    )
    status_note = _non_clean_status_note(statuses, language)
    if status_note:
        sentences.append(tr(status_note, language))

    policy_applied = [
        apply_wording_policy(
            sentence,
            lens=tr("Perception", language),
            status_flags={
                "unstable": unstable,
                "recommendation_blocked": (not recommendation_allowed and idx == 1),
            },
            language=language,
        )
        for idx, sentence in enumerate(sentences)
    ]
    policy_applied.append(competition_caveat_line(language))
    return policy_applied


def build_nms_explanations(
    nms_result: Any,
    currency: str,
    language: str | None = None,
) -> list[dict[str, str]]:
    max_trial_price = _fmt_price(_read_nms_field(nms_result, "max_trial_price"))
    max_revenue_price = _fmt_price(_read_nms_field(nms_result, "max_revenue_price"))
    included_n = _read_nms_field(nms_result, "included_n", "n/a")
    puki_filter_applied = bool(_read_nms_field(nms_result, "puki_filter_applied", False))
    puki_threshold = _read_nms_field(nms_result, "puki_threshold")
    weighting_applied = bool(_read_nms_field(nms_result, "weighting_applied", False))

    if puki_filter_applied and puki_threshold is not None:
        puki_value = f"<= {puki_threshold}"
    elif puki_filter_applied:
        puki_value = tr("Applied", language)
    else:
        puki_value = tr("Not applied", language)

    weighting_value = (
        tr("Weighted", language) if weighting_applied else tr("Unweighted fallback", language)
    )

    return [
        {
            "label": tr("Max Trial Price", language),
            "value": f"{max_trial_price} {currency}",
            "explanation": tr(NMS_GLOSSARY["Max Trial Price"], language),
        },
        {
            "label": tr("Max Revenue Price", language),
            "value": f"{max_revenue_price} {currency}",
            "explanation": tr(NMS_GLOSSARY["Max Revenue Price"], language),
        },
        {
            "label": tr("Included N", language),
            "value": str(included_n),
            "explanation": tr(NMS_GLOSSARY["Included N"], language),
        },
        {
            "label": tr("PUKI Filter", language),
            "value": puki_value,
            "explanation": tr(NMS_GLOSSARY["PUKI Filter"], language),
        },
        {
            "label": tr("Weighting", language),
            "value": weighting_value,
            "explanation": tr(NMS_GLOSSARY["Weighting"], language),
        },
    ]


def build_nms_summary(
    nms_result: Any,
    currency: str,
    segment_label: str,
    language: str | None = None,
) -> list[str]:
    selected_language = normalize_language(language)
    max_trial_price = _to_float(
        _read_nms_field(nms_result, "max_trial_price"), default=float("nan")
    )
    max_revenue_price = _to_float(
        _read_nms_field(nms_result, "max_revenue_price"), default=float("nan")
    )
    max_trial_text = _fmt_price(max_trial_price)
    max_revenue_text = _fmt_price(max_revenue_price)

    sentences = [
        (
            f"Das höchste Trial liegt bei {max_trial_text} {currency}."
            if selected_language == "de"
            else f"The highest trial is at {max_trial_text} {currency}."
        ),
        (
            f"Das höchste modellierte Revenue liegt bei {max_revenue_text} {currency}."
            if selected_language == "de"
            else f"The highest modeled revenue is at {max_revenue_text} {currency}."
        ),
        (
            "NMS Trial und Revenue sind modellierte Nachfrage-Proxys, keine beobachtete Nachfrage."
            if selected_language == "de"
            else "NMS trial and revenue are modeled demand proxies, not observed demand."
        ),
    ]

    if max_trial_text != "n/a" and max_revenue_text != "n/a":
        delta = max_revenue_price - max_trial_price
        if abs(delta) < 1e-9:
            sentences.append(
                "Trial- und Revenue-Peaks liegen auf demselben Preisniveau."
                if selected_language == "de"
                else "Trial and revenue peaks align at the same price level."
            )
        elif delta > 0:
            sentences.append(
                _pick_text(
                    selected_language,
                    (
                        "Revenue erreicht sein Maximum bei einem höheren Preis "
                        "als Trial; das deutet auf einen Monetarisierungs-"
                        "Trade-off hin."
                    ),
                    (
                        "Revenue peaks at a higher price than trial, "
                        "indicating a monetization trade-off."
                    ),
                )
            )
        else:
            sentences.append(
                _pick_text(
                    selected_language,
                    (
                        "Revenue erreicht sein Maximum bei einem niedrigeren "
                        "Preis als Trial; das deutet darauf hin, dass ein "
                        "früherer Preis das Modellergebnis maximiert."
                    ),
                    (
                        "Revenue peaks at a lower price than trial, "
                        "indicating earlier pricing maximizes the model output."
                    ),
                )
            )

    included_n = _read_nms_field(nms_result, "included_n")
    base_n = _read_nms_field(nms_result, "base_n")
    if included_n is not None and base_n is not None:
        sentences.append(
            _pick_text(
                selected_language,
                (
                    f"NMS nutzt {included_n} von {base_n} Befragten nach "
                    "Eligibility- und Vollständigkeitsprüfung."
                ),
                (
                    f"NMS uses {included_n} of {base_n} respondents after "
                    "eligibility and completeness checks."
                ),
            )
        )

    if not bool(_read_nms_field(nms_result, "weighting_applied", False)):
        sentences.append(
            _pick_text(
                selected_language,
                (
                    "NMS nutzte einen ungewichteten Fallback, weil keine "
                    "gültigen Gewichte verfügbar waren."
                ),
                ("NMS used an unweighted fallback because valid weights were not available."),
            )
        )

    filter_note = _read_nms_field(nms_result, "filter_note")
    if filter_note:
        sentences.append(tr(str(filter_note), language))

    if segment_label:
        sentences.append(
            f"Kontext: {segment_label}."
            if selected_language == "de"
            else f"Context: {segment_label}."
        )

    policy_applied = [
        apply_wording_policy(
            sentence,
            lens=tr("Modeled demand", language),
            language=language,
        )
        for sentence in sentences
    ]
    policy_applied.append(competition_caveat_line(language))
    return policy_applied


def build_turnover_explanations(
    turnover_result: Any,
    *,
    currency: str,
    source: str | None,
    language: str | None = None,
) -> list[dict[str, str]]:
    source_label, source_note = describe_turnover_source(source, language)
    return [
        {
            "label": tr("Max Turnover Price", language),
            "value": (
                f"{_fmt_price(getattr(turnover_result, 'max_turnover_price', None))} {currency}"
            ),
            "explanation": tr(TURNOVER_GLOSSARY["Max Turnover Price"], language),
        },
        {
            "label": tr("Max Turnover Index", language),
            "value": _fmt_price(getattr(turnover_result, "max_turnover_index", None)),
            "explanation": tr(TURNOVER_GLOSSARY["Max Turnover Index"], language),
        },
        {
            "label": tr("PI Source", language),
            "value": source_label,
            "explanation": f"{tr(TURNOVER_GLOSSARY['PI Source'], language)} {source_note}",
        },
    ]


def build_turnover_summary(
    turnover_result: Any,
    *,
    currency: str,
    segment_label: str,
    source: str | None,
    kpi_statuses: dict[str, str] | None = None,
    language: str | None = None,
) -> list[str]:
    selected_language = normalize_language(language)
    max_price = _fmt_price(getattr(turnover_result, "max_turnover_price", None))
    max_index = _fmt_price(getattr(turnover_result, "max_turnover_index", None))
    frame = getattr(turnover_result, "df", None)
    recommendation_allowed = (
        can_recommend(kpi_statuses, allow_interval=False) if kpi_statuses else True
    )
    unstable = not recommendation_allowed

    if recommendation_allowed:
        sentences = [
            _pick_text(
                selected_language,
                f"Der höchste Turnover wird bei einem Preis von {max_price} {currency} erreicht.",
                (
                    f"The highest turnover can be achieved by setting the "
                    f"price at {max_price} {currency}."
                ),
            ),
            _pick_text(
                selected_language,
                f"An diesem Punkt erreicht der Turnover Index {max_index} auf der 0-100-Skala.",
                f"At this point, the turnover index reaches {max_index} on the 0-100 scale.",
            ),
        ]
    else:
        sentences = [
            _pick_text(
                selected_language,
                (
                    "Turnover-Optimierung wird nicht für eine Zielpreisempfehlung "
                    "verwendet, weil die benötigten PSM-Schnittpunkte nicht clean "
                    "sind."
                ),
                (
                    "Turnover optimization is not used for a target-price "
                    "recommendation because required PSM intersections are not clean."
                ),
            ),
            _pick_text(
                selected_language,
                f"Der aktuelle diagnostische Wert des Turnover Index liegt bei {max_index}.",
                f"The current turnover index diagnostic value is {max_index}.",
            ),
        ]
    status_note = _non_clean_status_note(kpi_statuses, language)
    if status_note:
        sentences.append(status_note)
    if frame is not None and hasattr(frame, "sort_values"):
        sorted_frame = frame.sort_values("price").reset_index(drop=True)
        if len(sorted_frame) > 1:
            pi_peak_idx = int(sorted_frame["purchase_intention_pct"].astype(float).idxmax())
            pi_peak_price = float(sorted_frame.loc[pi_peak_idx, "price"])
            max_turnover_price = float(getattr(turnover_result, "max_turnover_price", 0.0))
            if max_turnover_price > pi_peak_price:
                sentences.append(
                    _pick_text(
                        selected_language,
                        (
                            "Der Turnover-Peak liegt oberhalb des PI-Peaks; "
                            "das deutet darauf hin, dass die Monetarisierung "
                            "einen höheren Preis als die reine Intention "
                            "begünstigt."
                        ),
                        (
                            "The turnover peak sits above the PI peak, "
                            "indicating monetization favors a higher price than "
                            "pure intent."
                        ),
                    )
                )
            elif max_turnover_price < pi_peak_price:
                sentences.append(
                    _pick_text(
                        selected_language,
                        (
                            "Der Turnover-Peak liegt unterhalb des PI-Peaks; "
                            "das deutet darauf hin, dass Turnover optimiert "
                            "wird, bevor die Intention ihr Maximum erreicht."
                        ),
                        (
                            "The turnover peak sits below the PI peak, "
                            "indicating turnover is optimized before intent "
                            "reaches its maximum."
                        ),
                    )
                )
            else:
                sentences.append(
                    _pick_text(
                        selected_language,
                        (
                            "PI und Turnover erreichen in dieser Sicht auf "
                            "demselben Preisniveau ihr Maximum."
                        ),
                        "PI and turnover peak at the same price level in this view.",
                    )
                )
    source_label, _source_note = describe_turnover_source(source, language)
    sentences.append(
        f"PI-Quelle in diesem Chart: {source_label}."
        if selected_language == "de"
        else f"PI source in this chart: {source_label}."
    )
    if segment_label:
        sentences.append(
            f"Kontext: {segment_label}."
            if selected_language == "de"
            else f"Context: {segment_label}."
        )

    policy_applied = [
        apply_wording_policy(
            sentence,
            lens=tr("Economics proxy", language),
            status_flags={
                "unstable": unstable,
                "recommendation_blocked": not recommendation_allowed,
            },
            language=language,
        )
        for sentence in sentences
    ]
    policy_applied.append(competition_caveat_line(language))
    return policy_applied


def build_profit_explanations(
    profit_result: Any,
    *,
    currency: str,
    language: str | None = None,
) -> list[dict[str, str]]:
    unit_cost = _fmt_price(getattr(profit_result, "unit_cost", None))
    max_price = _fmt_price(getattr(profit_result, "max_profit_price", None))
    max_index = _fmt_price(getattr(profit_result, "max_profit_index", None))
    return [
        {
            "label": tr("Unit Cost", language),
            "value": f"{unit_cost} {currency}",
            "explanation": tr(PROFIT_GLOSSARY["Unit Cost"], language),
        },
        {
            "label": tr("Max Profit Price", language),
            "value": f"{max_price} {currency}",
            "explanation": tr(PROFIT_GLOSSARY["Max Profit Price"], language),
        },
        {
            "label": tr("Max Profit Index", language),
            "value": max_index,
            "explanation": tr(PROFIT_GLOSSARY["Max Profit Index"], language),
        },
        {
            "label": tr("Break-even (Cost)", language),
            "value": f"{unit_cost} {currency}",
            "explanation": tr(PROFIT_GLOSSARY["Break-even (Cost)"], language),
        },
    ]


def build_profit_summary(
    profit_result: Any,
    *,
    currency: str,
    segment_label: str,
    product_label: str | None = None,
    kpi_statuses: dict[str, str] | None = None,
    language: str | None = None,
) -> list[str]:
    selected_language = normalize_language(language)
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
        break_even_context = (
            f"Für {product_clean} in {segment_clean}, "
            if selected_language == "de"
            else f"For {product_clean} in {segment_clean}, "
        )
    elif product_clean:
        break_even_context = (
            f"Für {product_clean}, " if selected_language == "de" else f"For {product_clean}, "
        )
    elif segment_clean:
        break_even_context = (
            f"Für {segment_clean}, " if selected_language == "de" else f"For {segment_clean}, "
        )
    else:
        break_even_context = ""

    recommendation_allowed = (
        can_recommend(kpi_statuses, allow_interval=False) if kpi_statuses else True
    )
    unstable = not recommendation_allowed
    if recommendation_allowed:
        sentences = [
            _pick_text(
                selected_language,
                (
                    f"Bei Stückkosten von {unit_cost} {currency} wird der "
                    f"höchste Profit-Proxy bei {max_price} {currency} erreicht."
                ),
                (
                    f"Given unit cost {unit_cost} {currency}, the highest "
                    f"profit proxy is achieved at {max_price} {currency}."
                ),
            ),
            _pick_text(
                selected_language,
                f"An diesem Punkt erreicht der Profit Index {max_index} auf der 0-100-Skala.",
                f"At this point, the profit index reaches {max_index} on the 0-100 scale.",
            ),
            _pick_text(
                selected_language,
                f"{break_even_context}der Break-even-Marker liegt bei {unit_cost} {currency}.",
                f"{break_even_context}the break-even marker is set at {unit_cost} {currency}.",
            ),
        ]
    else:
        sentences = [
            _pick_text(
                selected_language,
                (
                    "Profit-Optimierung wird nicht für eine Zielpreisempfehlung "
                    "verwendet, weil die benötigten PSM-Schnittpunkte nicht "
                    "clean sind."
                ),
                (
                    "Profit optimization is not used for a target-price "
                    "recommendation because required PSM intersections are not clean."
                ),
            ),
            _pick_text(
                selected_language,
                f"{break_even_context}der Break-even-Marker liegt bei {unit_cost} {currency}.",
                f"{break_even_context}the break-even marker is set at {unit_cost} {currency}.",
            ),
        ]
    status_note = _non_clean_status_note(kpi_statuses, language)
    if status_note:
        sentences.append(status_note)
    if math.isfinite(unit_cost_num) and math.isfinite(max_price_num):
        delta = max_price_num - unit_cost_num
        if delta > 0:
            sentences.append(
                _pick_text(
                    selected_language,
                    (
                        "Der Preis mit maximalem Profit liegt oberhalb des "
                        "Break-even; das deutet auf eine positive Stückmarge "
                        "am Optimum hin."
                    ),
                    (
                        "The maximum-profit price sits above break-even, "
                        "indicating positive unit margin at the optimum."
                    ),
                )
            )
        elif delta < 0:
            sentences.append(
                _pick_text(
                    selected_language,
                    (
                        "Der Preis mit maximalem Profit liegt unterhalb des "
                        "Break-even; das deutet darauf hin, dass das aktuelle "
                        "Setup am Optimum keine positive Stückmarge erreicht."
                    ),
                    (
                        "The maximum-profit price sits below break-even, "
                        "indicating the current setup does not reach positive "
                        "unit margin at the optimum."
                    ),
                )
            )
        else:
            sentences.append(
                _pick_text(
                    selected_language,
                    (
                        "Der Preis mit maximalem Profit entspricht dem "
                        "Break-even; das deutet auf eine Stückmarge von null "
                        "am Optimum hin."
                    ),
                    (
                        "The maximum-profit price equals break-even, "
                        "indicating a zero unit margin at the optimum."
                    ),
                )
            )
    if segment_label:
        sentences.append(
            f"Kontext: {segment_label}."
            if selected_language == "de"
            else f"Context: {segment_label}."
        )
    policy_applied = [
        apply_wording_policy(
            sentence,
            lens=tr("Economics proxy", language),
            status_flags={
                "unstable": unstable,
                "recommendation_blocked": not recommendation_allowed,
            },
            language=language,
        )
        for sentence in sentences
    ]
    policy_applied.append(competition_caveat_line(language))
    return policy_applied
