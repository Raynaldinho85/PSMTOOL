from __future__ import annotations

from psm_tool.i18n.runtime import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TranslationEntry,
    get_language,
    normalize_language,
    set_language,
    t,
    tr,
)


def get_knowledge_markdown(
    language: str,
    config_snapshot: dict,
    sav_available: bool,
) -> dict[str, str]:
    from psm_tool.i18n.knowledge import get_knowledge_markdown as _get_knowledge_markdown

    return _get_knowledge_markdown(language, config_snapshot, sav_available)


__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "TranslationEntry",
    "get_language",
    "get_knowledge_markdown",
    "normalize_language",
    "set_language",
    "t",
    "tr",
]
