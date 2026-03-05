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
