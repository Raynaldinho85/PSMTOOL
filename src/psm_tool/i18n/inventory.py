from __future__ import annotations

from typing import Any

from psm_tool.i18n.runtime import TRANSLATIONS
from psm_tool.ui.knowledge_content import get_knowledge_markdown_de, get_knowledge_markdown_en

INVENTORY_COLUMNS = ("key", "en", "de", "context", "location", "notes")


def _inventory_snapshot() -> dict[str, Any]:
    return {
        "default_currency_snap": {"EUR": 5.0, "SEK": 20.0, "CHF": 5.0},
        "supported_columns": [],
        "required_columns": [
            "bargain",
            "expensive_acceptable",
            "too_cheap",
            "too_expensive",
        ],
        "recommended_columns": ["currency", "product_id", "segment"],
        "optional_columns": ["puki", "weight"],
        "ordering_rule": "too_cheap < bargain < expensive_acceptable < too_expensive",
        "intersection_statuses": ["clean", "interval", "closest"],
        "pi_normalization_note_available": True,
        "pi_tiny_note_available": True,
    }


def build_translation_inventory() -> list[dict[str, str]]:
    rows = [
        {
            "key": key,
            "en": entry.en,
            "de": entry.de or entry.en,
            "context": entry.context,
            "location": entry.location,
            "notes": entry.notes,
        }
        for key, entry in sorted(TRANSLATIONS.items())
    ]

    snapshot = _inventory_snapshot()
    markdown_en = get_knowledge_markdown_en(snapshot, sav_available=False)
    markdown_de = get_knowledge_markdown_de(snapshot, sav_available=False)
    for tab_name, en_text in markdown_en.items():
        key = f"knowledge.markdown.{tab_name.lower().replace(' ', '_').replace('&', 'and')}"
        rows.append(
            {
                "key": key,
                "en": en_text,
                "de": markdown_de.get(tab_name, en_text),
                "context": "Knowledge & Methodology markdown tab content.",
                "location": "src/psm_tool/ui/knowledge_content.py",
                "notes": "Generated with representative config values; runtime values may vary.",
            }
        )
    return rows
