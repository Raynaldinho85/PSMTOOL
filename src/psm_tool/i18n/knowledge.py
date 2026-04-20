from __future__ import annotations

from psm_tool.i18n.runtime import normalize_language
from psm_tool.ui.knowledge_content import get_knowledge_markdown_de, get_knowledge_markdown_en


def get_knowledge_markdown(
    language: str,
    config_snapshot: dict,
    sav_available: bool,
) -> dict[str, str]:
    if normalize_language(language) == "de":
        return get_knowledge_markdown_de(config_snapshot, sav_available)
    return get_knowledge_markdown_en(config_snapshot, sav_available)
