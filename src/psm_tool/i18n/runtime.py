from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "de")
LANGUAGE_STATE_KEY = "app_language"
_REVIEW_CSV_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "i18n_translation_inventory_de_review.csv"
)
_LEGACY_CSV_PATH = Path(__file__).resolve().with_name("translations_inventory.csv")


@dataclass(frozen=True, slots=True)
class TranslationEntry:
    en: str
    de: str | None = None
    context: str = ""
    location: str = ""
    notes: str = ""


def _normalize_cell(value: object) -> str:
    return str(value or "").strip()


def _load_review_translations() -> dict[str, TranslationEntry]:
    if not _REVIEW_CSV_PATH.exists():
        return {}
    return _load_csv_translations(_REVIEW_CSV_PATH)


def _load_csv_translations(path: Path) -> dict[str, TranslationEntry]:
    loaded: dict[str, TranslationEntry] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = _normalize_cell(row.get("key"))
            en = _normalize_cell(row.get("en"))
            if not key or not en:
                continue
            loaded[key] = TranslationEntry(
                en=en,
                de=(
                    _normalize_cell(row.get("de_suggested"))
                    or _normalize_cell(row.get("de"))
                    or None
                ),
                context=_normalize_cell(row.get("context")),
                location=(
                    _normalize_cell(row.get("source_location"))
                    or _normalize_cell(row.get("location"))
                ),
                notes=_normalize_cell(row.get("notes")),
            )
    return loaded


_OVERRIDE_TRANSLATIONS: dict[str, TranslationEntry] = {
    "override.app.upload_step_no_sav": TranslationEntry(
        en="Load CSV/XLSX, validate template, or use demo data.",
        de="CSV/XLSX laden, Vorlage validieren oder Demodaten verwenden.",
    ),
    "override.upload.accepted_formats_no_sav": TranslationEntry(
        en="Accepted formats: CSV, XLSX",
        de="Akzeptierte Formate: CSV, XLSX",
    ),
    "override.upload.sav_disabled": TranslationEntry(
        en=(
            "SAV uploads are disabled in the app because uploaded files must be "
            "processed fully in-memory. Please convert SAV to CSV or XLSX first."
        ),
        de=(
            "SAV-Uploads sind in der App deaktiviert, weil hochgeladene Dateien "
            "vollständig im Arbeitsspeicher verarbeitet werden müssen. Bitte SAV "
            "vorher in CSV oder XLSX konvertieren."
        ),
    ),
    "override.knowledge.sav_disabled": TranslationEntry(
        en=(
            "SAV uploads are intentionally disabled in the app so uploaded files "
            "remain fully in-memory."
        ),
        de=(
            "SAV-Uploads sind in der App bewusst deaktiviert, damit hochgeladene "
            "Dateien vollständig im Arbeitsspeicher bleiben."
        ),
    ),
    "nav.knowledge": TranslationEntry(en="Knowledge", de="Methodik"),
    "knowledge.title": TranslationEntry(en="Knowledge & Methodology", de="Wissen & Methodik"),
    "knowledge.tab.overview": TranslationEntry(en="Overview", de="Überblick"),
    "knowledge.tab.quality_grid": TranslationEntry(en="Quality & Grid", de="Qualität & Grid"),
    "knowledge.tab.exports_privacy": TranslationEntry(
        en="Exports & Privacy",
        de="Export & Datenschutz",
    ),
    "knowledge.tab.faq": TranslationEntry(en="FAQ", de="Häufige Fragen"),
    "override.results.economics": TranslationEntry(en="Economics", de="Ökonomik"),
    "override.term.pmi": TranslationEntry(
        en="Point of Marginal Inexpensiveness",
        de="Untere Akzeptanzgrenze",
    ),
    "override.term.pmi_alt": TranslationEntry(
        en="Point of Marginal Cheapness",
        de="Untere Akzeptanzgrenze",
    ),
    "override.term.opp": TranslationEntry(
        en="Optimal Pricing Point",
        de="Optimaler Preispunkt",
    ),
    "override.term.opp_alt": TranslationEntry(
        en="Optimal Price Point",
        de="Optimaler Preispunkt",
    ),
    "override.term.idp": TranslationEntry(
        en="Indifference Pricing Point",
        de="Indifferenzpreispunkt",
    ),
    "override.term.idp_alt": TranslationEntry(
        en="Indifference Price Point",
        de="Indifferenzpreispunkt",
    ),
    "override.term.pme": TranslationEntry(
        en="Point of Marginal Expensiveness",
        de="Obere Akzeptanzgrenze",
    ),
    "override.economics_proxy": TranslationEntry(
        en="Economics proxy",
        de="Ökonomik-Proxy",
    ),
    "override.perception": TranslationEntry(en="Perception", de="Wahrnehmung"),
    "override.modeled_demand": TranslationEntry(
        en="Modeled demand",
        de="Modellierte Nachfrage",
    ),
    "override.summary.none": TranslationEntry(
        en="No summary available.",
        de="Keine Zusammenfassung verfügbar.",
    ),
    "override.results.pi_unit_note": TranslationEntry(
        en="PI unit note: {note}",
        de="Hinweis zur PI-Einheit: {note}",
    ),
    "override.results.requires_clean_opp": TranslationEntry(
        en="Requires clean OPP for optimization statements.",
        de="Erfordert einen cleanen OPP für Optimierungsaussagen.",
    ),
    "override.results.requires_clean_pmi_pme": TranslationEntry(
        en="Requires clean PMI and PME for optimization statements.",
        de="Erfordert cleane PMI- und PME-Schnittpunkte für Optimierungsaussagen.",
    ),
    "override.results.p05_p95": TranslationEntry(
        en="P05/P95: {p05_label} / {p95_label}",
        de="P05/P95: {p05_label} / {p95_label}",
    ),
    "override.status.applied": TranslationEntry(en="Applied", de="Angewendet"),
    "override.status.not_applied": TranslationEntry(
        en="Not applied",
        de="Nicht angewendet",
    ),
    "override.status.weighted": TranslationEntry(en="Weighted", de="Gewichtet"),
    "override.status.unweighted": TranslationEntry(
        en="Unweighted fallback",
        de="Ungewichteter Fallback",
    ),
    "override.nms.included_n": TranslationEntry(en="Included N", de="Eingeschlossenes n"),
    "override.nms.puki_filter": TranslationEntry(en="PUKI Filter", de="PUKI-Filter"),
    "override.nms.weighting": TranslationEntry(en="Weighting", de="Gewichtung"),
    "override.io.required_columns": TranslationEntry(
        en="Missing required columns: {missing_columns}",
        de="Fehlende Pflichtspalten: {missing_columns}",
    ),
    "override.io.pi_ladder_missing": TranslationEntry(
        en="Purchase intention ladder missing required columns: {required_columns}",
        de="Preisleiter für Kaufabsicht fehlt erforderliche Spalten: {required_columns}",
    ),
    "override.io.negative_ladder_prices": TranslationEntry(
        en="Negative ladder prices treated as missing: {negative_price_count} rows.",
        de=(
            "Negative Preisleiter-Werte wurden als fehlend behandelt: "
            "{negative_price_count} Zeilen."
        ),
    ),
    "override.io.sav_dependency": TranslationEntry(
        en=(
            "SAV support requires optional dependency 'pyreadstat'. Install in this repo "
            'with: pip install -e .[sav] (or from package index: pip install "psm-tool[sav]").'
        ),
        de=(
            "SAV-Unterstützung erfordert die optionale Abhängigkeit 'pyreadstat'. "
            "Installation in diesem Repo mit: pip install -e .[sav] "
            '(oder aus dem Package Index: pip install "psm-tool[sav]").'
        ),
    ),
    "override.core.puki_missing": TranslationEntry(
        en="PUKI filter not applied because 'puki' column is missing.",
        de="PUKI-Filter wurde nicht angewendet, weil die Spalte 'puki' fehlt.",
    ),
    "override.core.nms_requires": TranslationEntry(
        en="NMS requires columns: {required}. Missing: {missing}",
        de="NMS benötigt folgende Spalten: {required}. Fehlend: {missing}",
    ),
    "override.kpi.interval_suffix": TranslationEntry(
        en="{base_explanation}; interval estimate",
        de="{base_explanation}; Intervallschätzung",
    ),
    "override.kpi.diagnostic_suffix": TranslationEntry(
        en="{base_explanation}; diagnostic",
        de="{base_explanation}; diagnostisch",
    ),
    "override.export.preflight_failed": TranslationEntry(
        en="Static export preflight failed: {error}",
        de="Preflight für statischen Export fehlgeschlagen: {error}",
    ),
    "override.report.intersection_status": TranslationEntry(
        en="Intersection status: {statuses}.",
        de="Schnittpunktstatus: {statuses}.",
    ),
    "override.report.max_turnover_index": TranslationEntry(
        en="Max Turnover Index",
        de="Maximaler Turnover Index",
    ),
    "override.report.unit_cost": TranslationEntry(en="Unit Cost", de="Stückkosten"),
    "override.report.max_profit_price": TranslationEntry(
        en="Max Profit Price",
        de="Preis mit maximalem Profit",
    ),
    "override.report.max_profit_index": TranslationEntry(
        en="Max Profit Index",
        de="Maximaler Profit Index",
    ),
    "override.pptx.turnover_diagnostics": TranslationEntry(
        en="Economics proxy: Model suggests turnover diagnostics only.",
        de="Ökonomik-Proxy: Das Modell liefert nur Turnover-Diagnostik.",
    ),
    "override.pptx.nms_diagnostics": TranslationEntry(
        en="Modeled demand: Model suggests NMS diagnostics.",
        de="Modellierte Nachfrage: Das Modell liefert nur NMS-Diagnostik.",
    ),
    "override.pptx.profit_diagnostics": TranslationEntry(
        en="Economics proxy: Model suggests profit diagnostics only.",
        de="Ökonomik-Proxy: Das Modell liefert nur Profit-Diagnostik.",
    ),
    "override.pptx.accepted_range": TranslationEntry(
        en="Accepted range: {accepted_range_text}",
        de="Akzeptierter Preisbereich: {accepted_range_text}",
    ),
    "override.pptx.price_stress": TranslationEntry(
        en="Price stress (OPP-IDP): {stress_text}",
        de="Price Stress (OPP-IDP): {stress_text}",
    ),
    "override.pptx.max_trial": TranslationEntry(
        en="Max Trial: {currency} {price:.2f}",
        de="Max Trial: {currency} {price:.2f}",
    ),
    "override.pptx.max_revenue": TranslationEntry(
        en="Max Revenue: {currency} {price:.2f}",
        de="Max Revenue: {currency} {price:.2f}",
    ),
    "override.pptx.included_n_line": TranslationEntry(
        en="Included N: {included_n}",
        de="Eingeschlossenes n: {included_n}",
    ),
    "override.pptx.opp_blocked": TranslationEntry(
        en="OPP recommendation is blocked because PSM intersections are not clean.",
        de="OPP-Empfehlung ist blockiert, weil die PSM-Schnittpunkte nicht clean sind.",
    ),
    "override.pptx.turnover_blocked": TranslationEntry(
        en="Turnover target-price recommendation is blocked due to non-clean intersections.",
        de="Turnover-Zielpreisempfehlung ist wegen nicht-cleaner Schnittpunkte blockiert.",
    ),
    "override.pptx.profit_blocked": TranslationEntry(
        en="Profit target-price recommendation is blocked due to non-clean intersections.",
        de="Profit-Zielpreisempfehlung ist wegen nicht-cleaner Schnittpunkte blockiert.",
    ),
    "override.pptx.outlier_filter_band": TranslationEntry(
        en="Outlier filter: {level} ({q_low:.1f}%-{q_high:.1f}%), excluded n={excluded}",
        de="Ausreißerfilter: {level} ({q_low:.1f}%-{q_high:.1f}%), ausgeschlossenes n={excluded}",
    ),
    "override.pptx.outlier_filter_simple": TranslationEntry(
        en="Outlier filter: {level}, excluded n={excluded}",
        de="Ausreißerfilter: {level}, ausgeschlossenes n={excluded}",
    ),
    "override.kpi_summary.title": TranslationEntry(
        en="KPI Summary",
        de="KPI-Übersicht",
    ),
    "override.kpi_summary.context": TranslationEntry(
        en="Product: {product} | Country: {country} | Currency: {currency}",
        de="Produkt: {product} | Land: {country} | Währung: {currency}",
    ),
    "override.kpi_summary.not_available": TranslationEntry(
        en="Not available",
        de="Nicht verfügbar",
    ),
}


def _build_translations() -> dict[str, TranslationEntry]:
    translations = _load_review_translations()
    if _LEGACY_CSV_PATH.exists():
        for key, entry in _load_csv_translations(_LEGACY_CSV_PATH).items():
            translations.setdefault(key, entry)
    translations.update(_OVERRIDE_TRANSLATIONS)
    return translations


TRANSLATIONS: dict[str, TranslationEntry] = _build_translations()
TRANSLATIONS_BY_EN: dict[str, TranslationEntry] = {}
for entry in TRANSLATIONS.values():
    TRANSLATIONS_BY_EN[entry.en] = entry


def normalize_language(language: Any) -> str:
    value = str(language or "").lower().strip()
    if value in SUPPORTED_LANGUAGES:
        return value
    return DEFAULT_LANGUAGE


def get_language() -> str:
    language = normalize_language(st.session_state.get(LANGUAGE_STATE_KEY, DEFAULT_LANGUAGE))
    st.session_state[LANGUAGE_STATE_KEY] = language
    return language


def set_language(language: Any) -> str:
    normalized = normalize_language(language)
    st.session_state[LANGUAGE_STATE_KEY] = normalized
    return normalized


def _resolve_language(language: str | None) -> str:
    return normalize_language(language) if language is not None else get_language()


def _select_text(entry: TranslationEntry, *, language: str | None) -> str:
    selected_language = _resolve_language(language)
    if selected_language == "de" and entry.de:
        return entry.de
    return entry.en


def t(key: str, language: str | None = None, **kwargs: Any) -> str:
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key.format(**kwargs) if kwargs else key
    text = _select_text(entry, language=language)
    return text.format(**kwargs) if kwargs else text


def tr(source_text: str, language: str | None = None, **kwargs: Any) -> str:
    entry = TRANSLATIONS_BY_EN.get(source_text)
    text = _select_text(entry, language=language) if entry is not None else source_text
    return text.format(**kwargs) if kwargs else text
