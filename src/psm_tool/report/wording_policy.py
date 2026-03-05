from __future__ import annotations

import re
from collections.abc import Mapping

COMPETITION_CAVEAT = "No competition/substitution model is included."

_IMPERATIVE_PATTERNS = [
    (re.compile(r"\bSet price at\b", re.IGNORECASE), "Model suggests a price around"),
    (re.compile(r"\bSet price in\b", re.IGNORECASE), "Model suggests a price within"),
    (re.compile(r"\bUse price\b", re.IGNORECASE), "Model suggests using a price around"),
    (re.compile(r"\bOptimal price is\b", re.IGNORECASE), "Model suggests a price around"),
    (re.compile(r"\bMaximize\b", re.IGNORECASE), "Model suggests prioritizing"),
    (re.compile(r"\bOptimize\b", re.IGNORECASE), "Model suggests optimizing"),
]


def can_recommend(
    kpi_statuses: Mapping[str, str] | list[str] | tuple[str, ...],
    *,
    allow_interval: bool = False,
) -> bool:
    """Return whether recommendation language is allowed for current KPI statuses."""
    if isinstance(kpi_statuses, Mapping):
        statuses = [str(value) for value in kpi_statuses.values()]
    else:
        statuses = [str(value) for value in kpi_statuses]

    if not statuses:
        return False
    if any(status == "closest" for status in statuses):
        return False
    if any(status == "interval" for status in statuses):
        return bool(allow_interval)
    return all(status == "clean" for status in statuses)


def apply_wording_policy(
    text: str,
    lens: str,
    status_flags: Mapping[str, bool] | None = None,
) -> str:
    """Apply deterministic wording rules for lens labels and recommendation phrasing."""
    content = " ".join(str(text).strip().split())
    if not content:
        return f"{lens}:"

    for pattern, replacement in _IMPERATIVE_PATTERNS:
        content = pattern.sub(replacement, content)

    if not re.search(r"\bModel suggests\b", content, re.IGNORECASE):
        content = f"Model suggests {content}"

    if "under current assumptions" not in content:
        content = content.rstrip(".")
        content = f"{content} under current assumptions."

    flags = status_flags or {}
    if flags.get("unstable"):
        content = content.rstrip(".")
        content = f"{content}; interpret with caution."
    if flags.get("recommendation_blocked"):
        content = content.rstrip(".")
        content = f"{content}; no target-price recommendation is issued."

    return f"{lens}: {content}"


def competition_caveat_line() -> str:
    return COMPETITION_CAVEAT
