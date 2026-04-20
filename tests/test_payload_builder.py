from __future__ import annotations

import pandas as pd

from psm_tool.report.payload_builder import build_export_payload_from_dataset


def _dataset() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for product in ["Classic", "Premium"]:
        for segment, currency in [("DE", "EUR"), ("CH", "CHF")]:
            for idx in range(16):
                base = 40 + idx
                rows.append(
                    {
                        "respondent_id": f"{product}-{segment}-{idx}",
                        "product_id": product,
                        "segment": segment,
                        "currency": currency,
                        "too_cheap": float(base),
                        "bargain": float(base + 10),
                        "expensive_acceptable": float(base + 20),
                        "too_expensive": float(base + 30),
                        "pi_bargain_pct": float(70 - (idx % 8)),
                        "pi_expensive_pct": float(52 - (idx % 6)),
                        "puki": 2,
                    }
                )
    return pd.DataFrame(rows)


def _dataset_with_neutral_puki_psm_effect() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "respondent_id": "a",
                "product_id": "Classic",
                "segment": "DE",
                "currency": "EUR",
                "too_cheap": 10.0,
                "bargain": 20.0,
                "expensive_acceptable": 30.0,
                "too_expensive": 40.0,
                "pi_bargain_pct": 80.0,
                "pi_expensive_pct": 40.0,
                "puki": 2,
            },
            {
                "respondent_id": "b",
                "product_id": "Classic",
                "segment": "DE",
                "currency": "EUR",
                "too_cheap": 12.0,
                "bargain": 22.0,
                "expensive_acceptable": 32.0,
                "too_expensive": 42.0,
                "pi_bargain_pct": 75.0,
                "pi_expensive_pct": 35.0,
                "puki": 2,
            },
            {
                "respondent_id": "c",
                "product_id": "Classic",
                "segment": "DE",
                "currency": "EUR",
                "too_cheap": 30.0,
                "bargain": 50.0,
                "expensive_acceptable": 70.0,
                "too_expensive": 90.0,
                "pi_bargain_pct": 90.0,
                "pi_expensive_pct": 80.0,
                "puki": 3,
            },
            {
                "respondent_id": "d",
                "product_id": "Classic",
                "segment": "DE",
                "currency": "EUR",
                "too_cheap": 32.0,
                "bargain": 52.0,
                "expensive_acceptable": 72.0,
                "too_expensive": 92.0,
                "pi_bargain_pct": 95.0,
                "pi_expensive_pct": 85.0,
                "puki": 3,
            },
        ]
    )


def test_payload_builder_generates_all_product_country_analyses() -> None:
    payload = build_export_payload_from_dataset(_dataset(), snap_enabled=True)
    analyses = payload["analyses"]
    assert len(analyses) == 4
    pairs = {(a["product_id"], a["segment"]) for a in analyses}
    assert pairs == {
        ("Classic", "DE"),
        ("Classic", "CH"),
        ("Premium", "DE"),
        ("Premium", "CH"),
    }


def test_payload_builder_includes_turnover_from_nms_fallback_when_ladder_absent() -> None:
    payload = build_export_payload_from_dataset(_dataset(), snap_enabled=True)
    analysis = payload["analyses"][0]
    assert analysis["turnover_source"] == "nms_trial"
    assert analysis["turnover_index_result"] is not None


def test_payload_builder_applies_puki_threshold_to_exported_psm() -> None:
    df = _dataset_with_neutral_puki_psm_effect()

    strict = build_export_payload_from_dataset(df, snap_enabled=False, puki_threshold=2)
    neutral = build_export_payload_from_dataset(df, snap_enabled=False, puki_threshold=3)

    strict_analysis = strict["analyses"][0]
    neutral_analysis = neutral["analyses"][0]

    assert strict_analysis["puki_excluded_from_analysis_n"] == 2
    assert neutral_analysis["puki_excluded_from_analysis_n"] == 0
    assert strict_analysis["kpis"]["opp"] != neutral_analysis["kpis"]["opp"]
    assert len(strict_analysis["curves"]) != len(neutral_analysis["curves"])


def test_payload_builder_attaches_active_tested_price_by_product_country() -> None:
    df = _dataset_with_neutral_puki_psm_effect()

    payload = build_export_payload_from_dataset(
        df,
        snap_enabled=False,
        tested_price_by_key={"Classic::DE": 25.0},
        tested_price_active_by_key={"Classic::DE": True},
    )

    analysis = payload["analyses"][0]
    assert analysis["tested_price"] == 25.0
    assert analysis["tested_price_active"] is True


def test_payload_builder_ignores_inactive_or_invalid_tested_price() -> None:
    df = _dataset_with_neutral_puki_psm_effect()

    inactive = build_export_payload_from_dataset(
        df,
        snap_enabled=False,
        tested_price_by_key={"Classic::DE": 25.0},
        tested_price_active_by_key={"Classic::DE": False},
    )
    invalid = build_export_payload_from_dataset(
        df,
        snap_enabled=False,
        tested_price_by_key={"Classic::DE": 0.0},
        tested_price_active_by_key={"Classic::DE": True},
    )

    assert inactive["analyses"][0]["tested_price"] is None
    assert inactive["analyses"][0]["tested_price_active"] is False
    assert invalid["analyses"][0]["tested_price"] is None
    assert invalid["analyses"][0]["tested_price_active"] is False


def test_payload_builder_attaches_marker_label_overrides_by_product_country() -> None:
    df = _dataset_with_neutral_puki_psm_effect()

    payload = build_export_payload_from_dataset(
        df,
        snap_enabled=False,
        marker_label_side_overrides_by_key={
            "Classic::DE": {
                "psm": {"pmi": "left", "opp": "auto", "pme": "right"},
                "nms": {"max_trial": "left"},
            }
        },
    )

    overrides = payload["analyses"][0]["marker_label_side_overrides"]
    assert overrides == {
        "psm": {"pmi": "left", "pme": "right"},
        "nms": {"max_trial": "left"},
    }
