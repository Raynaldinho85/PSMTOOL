from __future__ import annotations

import importlib.util
from pathlib import Path

from psm_tool.ui.knowledge_content import (
    get_knowledge_markdown_de,
    get_knowledge_markdown_en,
)

REQUIRED_TABS = [
    "Overview",
    "PSM (Price Sensitivity Meter)",
    "NMS (Newton-Miller-Smith)",
    "Quality & Grid",
    "Exports & Privacy",
    "FAQ",
]


def _snapshot() -> dict:
    return {
        "default_currency_snap": {"EUR": 5.0, "SEK": 20.0, "CHF": 5.0},
        "ordering_rule": "too_cheap < bargain < expensive_acceptable < too_expensive",
        "intersection_statuses": ["clean", "interval", "closest"],
        "pi_normalization_note_available": True,
        "pi_tiny_note_available": True,
        "supported_columns": [
            "respondent_id",
            "segment",
            "currency",
            "too_cheap",
            "bargain",
            "expensive_acceptable",
            "too_expensive",
        ],
    }


def test_knowledge_markdown_en_returns_required_non_empty_tabs() -> None:
    result = get_knowledge_markdown_en(_snapshot(), sav_available=False)
    for tab in REQUIRED_TABS:
        assert tab in result
        assert isinstance(result[tab], str)
        assert result[tab].strip() != ""


def test_knowledge_markdown_de_returns_required_non_empty_tabs() -> None:
    result = get_knowledge_markdown_de(_snapshot(), sav_available=True)
    for tab in REQUIRED_TABS:
        assert tab in result
        assert isinstance(result[tab], str)
        assert result[tab].strip() != ""


def test_knowledge_markdown_contains_currency_snap_mapping() -> None:
    result_en = get_knowledge_markdown_en(_snapshot(), sav_available=False)
    quality_text = result_en["Quality & Grid"]
    assert "EUR: 5" in quality_text
    assert "SEK: 20" in quality_text
    assert "CHF: 5" in quality_text


def test_knowledge_markdown_contains_code_level_method_details() -> None:
    result_en = get_knowledge_markdown_en(_snapshot(), sav_available=False)
    assert "read_any" in result_en["Overview"]
    assert "validate_template" in result_en["Overview"]
    assert (
        "too_cheap < bargain < expensive_acceptable < too_expensive"
        in result_en["PSM (Price Sensitivity Meter)"]
    )
    assert "revenue_raw(p) = price(p) * (PI(p)/100)" in result_en["NMS (Newton-Miller-Smith)"]
    assert "round_up_to_100(2 * median_expensive_acceptable)" in result_en["Quality & Grid"]
    assert "closest" in result_en["PSM (Price Sensitivity Meter)"]
    assert "Negative price values are treated as missing" in result_en["Quality & Grid"]
    assert "coded scale `1..11`" in result_en["NMS (Newton-Miller-Smith)"]
    assert "pct = 10 + (code - 1) * 9" in result_en["NMS (Newton-Miller-Smith)"]
    assert "Model Layers" in result_en["Overview"]
    assert "PSM measures price perception boundaries, not observed market demand under competition." in result_en[
        "Overview"
    ]


def test_knowledge_page_file_imports_without_errors() -> None:
    module_path = Path("src/psm_tool/ui/pages/4_knowledge.py")
    spec = importlib.util.spec_from_file_location("knowledge_page_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "main")
