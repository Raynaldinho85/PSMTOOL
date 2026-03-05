from __future__ import annotations

from psm_tool.report.wording_policy import (
    apply_wording_policy,
    can_recommend,
    competition_caveat_line,
)


def test_can_recommend_clean_only_by_default() -> None:
    assert can_recommend({"pmi": "clean", "opp": "clean"}) is True
    assert can_recommend({"pmi": "interval", "opp": "clean"}) is False
    assert can_recommend({"pmi": "closest", "opp": "clean"}) is False


def test_can_recommend_allows_interval_when_enabled() -> None:
    assert can_recommend({"pmi": "interval", "opp": "clean"}, allow_interval=True) is True


def test_apply_wording_policy_adds_lens_and_assumption_phrase() -> None:
    text = apply_wording_policy("Set price at 10 EUR.", lens="Perception")
    assert text.startswith("Perception: ")
    assert "Model suggests" in text
    assert "under current assumptions" in text
    assert "Set price at" not in text


def test_apply_wording_policy_marks_unstable_and_blocked() -> None:
    text = apply_wording_policy(
        "Optimal price is 10 EUR.",
        lens="Economics proxy",
        status_flags={"unstable": True, "recommendation_blocked": True},
    )
    assert "interpret with caution" in text
    assert "no target-price recommendation is issued" in text


def test_competition_caveat_is_fixed() -> None:
    assert competition_caveat_line() == "No competition/substitution model is included."
