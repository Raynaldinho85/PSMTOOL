from __future__ import annotations

from pathlib import Path

from psm_tool.i18n.inventory import INVENTORY_COLUMNS, build_translation_inventory
from psm_tool.i18n.runtime import TRANSLATIONS, TranslationEntry, normalize_language, t
from psm_tool.ui.page_nav import PAGE_ORDER


def test_normalize_language_defaults_to_english() -> None:
    assert normalize_language(None) == "en"
    assert normalize_language("fr") == "en"
    assert normalize_language("EN") == "en"
    assert normalize_language("de") == "de"


def test_translation_lookup_falls_back_to_english(monkeypatch) -> None:
    monkeypatch.setitem(
        TRANSLATIONS,
        "test.fallback",
        TranslationEntry(
            en="English fallback",
            de=None,
            context="Test fallback entry.",
            location="tests/test_i18n.py",
        ),
    )

    assert t("test.fallback", "de") == "English fallback"
    assert t("missing.translation.key", "de") == "missing.translation.key"


def test_navigation_items_use_translation_keys() -> None:
    assert [item.key for item in PAGE_ORDER] == ["app", "upload", "results", "export", "knowledge"]
    for item in PAGE_ORDER:
        assert item.label_key in TRANSLATIONS
        assert t(item.label_key, "en")
        assert t(item.label_key, "de")


def test_translation_inventory_contains_scoped_columns_and_knowledge_content() -> None:
    rows = build_translation_inventory()
    assert rows
    for row in rows:
        assert tuple(row.keys()) == INVENTORY_COLUMNS

    keys = {row["key"] for row in rows}
    assert "nav.results" in keys
    assert "knowledge.title" in keys
    assert "knowledge.markdown.overview" in keys
    assert "knowledge.markdown.quality_and_grid" in keys


def test_knowledge_page_no_longer_has_local_language_radio() -> None:
    source = Path("src/psm_tool/ui/pages/4_knowledge.py").read_text(encoding="utf-8")

    assert "st.radio" not in source
    assert "Language / Sprache" not in source
    assert "get_language()" in source


def test_language_switch_uses_compact_language_buttons_not_radio() -> None:
    source = Path("src/psm_tool/ui/page_nav.py").read_text(encoding="utf-8")

    assert "st.sidebar.radio" not in source
    assert "st.button(" in source
    assert '"EN"' in source
    assert '"DE"' in source
    assert 'width="content"' in source
    assert 'set_language("en")' in source
    assert 'set_language("de")' in source


def test_app_bottom_nav_keeps_language_switch_and_next_link() -> None:
    source = Path("src/psm_tool/ui/page_nav.py").read_text(encoding="utf-8")

    assert 'if current_key == "app":' in source
    assert "render_language_switch()" in source
    assert "label=f\"{t('nav.next')}: {t(next_item.label_key)}\"" in source


def test_quick_navigation_detection_covers_current_labels() -> None:
    source = Path("src/psm_tool/ui/style.py").read_text(encoding="utf-8")

    assert 'label.startsWith("Previous: ")' in source
    assert 'label.startsWith("Next: ")' in source
    assert 'label.startsWith("Zurueck: ")' in source
    assert 'label.startsWith("Weiter: ")' in source
    assert 'block.style.display = collapsed ? "block" : "none";' in source


def test_language_button_sidebar_css_targets_sidebar_section() -> None:
    source = Path("src/psm_tool/ui/style.py").read_text(encoding="utf-8")

    assert 'section[data-testid="stSidebar"] button[kind]' in source
    assert 'section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]' in source


def test_sidebar_nav_labels_are_localized_for_de_without_routing_changes() -> None:
    source = Path("src/psm_tool/ui/style.py").read_text(encoding="utf-8")

    assert 'const textTarget = labelNode.querySelector("p, span") || labelNode;' in source
    assert 'normalized === "results"' in source
    assert 'textTarget.textContent = deActive ? "ergebnisse" : originalLabel;' in source
    assert 'normalized === "knowledge"' in source
    assert 'textTarget.textContent = deActive ? "methodik" : originalLabel;' in source
