from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from psm_tool.report.insights import (
    build_kpi_explanations,
    build_nms_explanations,
    build_nms_summary,
    build_profit_explanations,
    build_profit_summary,
    build_psm_summary,
    build_turnover_explanations,
    build_turnover_summary,
    describe_turnover_source,
)


def _base_kpis() -> dict[str, float | str]:
    return {
        "pmi": 90.0,
        "opp": 100.0,
        "idp": 100.0,
        "pme": 110.0,
        "accepted_low": 90.0,
        "accepted_high": 110.0,
        "price_stress": 0.0,
        "stress_flag": "neutral",
        "pmi_status": "clean",
        "opp_status": "clean",
        "idp_status": "clean",
        "pme_status": "clean",
    }


def test_build_kpi_explanations_returns_label_value_explanation_rows() -> None:
    rows = build_kpi_explanations(_base_kpis())

    labels = [row["label"] for row in rows]
    assert labels == ["PMI", "OPP", "IDP", "PME", "Accepted Range", "Price Stress"]
    assert all({"label", "value", "explanation"} <= row.keys() for row in rows)


def test_build_psm_summary_negative_stress_branch() -> None:
    kpis = _base_kpis()
    kpis["opp"] = 90.0
    kpis["idp"] = 100.0
    lines = build_psm_summary(kpis, currency="EUR", segment_label="DE")

    assert lines[0] == "The accepted price range is between 90.00 EUR (PMI) and 110.00 EUR (PME)."
    assert lines[1] == "The optimal pricing point (OPP) is around 90.00 EUR."
    assert any("Price stress is negative" in line for line in lines)


def test_build_psm_summary_balanced_and_narrow_note() -> None:
    kpis = _base_kpis()
    kpis["pmi"] = 95.0
    kpis["pme"] = 104.0
    kpis["opp"] = 102.0
    kpis["idp"] = 100.0

    lines = build_psm_summary(kpis, currency="EUR", segment_label="DE")
    assert any("balanced pricing position" in line for line in lines)
    assert any("narrow" in line for line in lines)


def test_build_psm_summary_positive_stress_and_wide_note_and_caution() -> None:
    kpis = _base_kpis()
    kpis["pmi"] = 50.0
    kpis["pme"] = 120.0
    kpis["opp"] = 110.0
    kpis["idp"] = 100.0
    kpis["opp_status"] = "closest"

    lines = build_psm_summary(kpis, currency="EUR", segment_label="DE")
    assert any("Price stress is positive" in line for line in lines)
    assert any("wide" in line for line in lines)
    assert any("not clean" in line for line in lines)


def test_build_psm_summary_excludes_turnover_trial_and_includes_idp_sentence() -> None:
    lines = build_psm_summary(
        _base_kpis(),
        currency="EUR",
        segment_label="DE",
        nms_kpis={"max_revenue_price": 120.0, "max_trial_price": 90.0},
    )

    assert not any("highest turnover" in line for line in lines)
    assert not any("highest trial" in line for line in lines)
    assert any("Indifference Price Point of" in line for line in lines)


def test_build_psm_summary_with_product_country_parenthetical() -> None:
    lines = build_psm_summary(
        _base_kpis(),
        currency="EUR",
        segment_label="DE",
        product_label="Classic",
    )
    assert "for Classic in DE" in lines[0]
    assert "(PMI)" in lines[0]


def _base_nms_result() -> dict[str, object]:
    return {
        "max_trial_price": 90.0,
        "max_revenue_price": 120.0,
        "base_n": 100,
        "included_n": 80,
        "puki_filter_applied": True,
        "puki_threshold": 2,
        "weighting_applied": True,
        "filter_note": None,
    }


def test_build_nms_explanations_returns_expected_rows() -> None:
    rows = build_nms_explanations(_base_nms_result(), currency="EUR")
    labels = [row["label"] for row in rows]
    assert labels == [
        "Max Trial Price",
        "Max Revenue Price",
        "Included N",
        "PUKI Filter",
        "Weighting",
    ]
    assert rows[0]["value"] == "90.00 EUR"
    assert rows[1]["value"] == "120.00 EUR"
    assert rows[3]["value"] == "<= 2"


def test_build_nms_summary_aligned_peaks() -> None:
    nms_result = _base_nms_result()
    nms_result["max_revenue_price"] = 90.0
    lines = build_nms_summary(nms_result, currency="EUR", segment_label="DE")
    assert lines[0] == "The highest trial is at 90.00 EUR."
    assert lines[1] == "The highest modeled revenue is at 90.00 EUR."
    assert any("align at the same price level" in line for line in lines)
    assert any("uses 80 of 100 respondents" in line for line in lines)


def test_build_nms_summary_tradeoff_and_weight_fallback_note() -> None:
    nms_result = _base_nms_result()
    nms_result["weighting_applied"] = False
    nms_result["filter_note"] = "PUKI filter not applied because 'puki' column is missing."
    lines = build_nms_summary(nms_result, currency="EUR", segment_label="DE")
    assert any("higher price than trial" in line for line in lines)
    assert any("unweighted fallback" in line for line in lines)
    assert any("PUKI filter not applied" in line for line in lines)


def test_build_turnover_explanations_and_summary() -> None:
    turnover = SimpleNamespace(
        max_turnover_price=200.0,
        max_turnover_index=100.0,
        df=pd.DataFrame(
            {
                "price": [100.0, 200.0, 300.0],
                "purchase_intention_pct": [60.0, 50.0, 20.0],
            }
        ),
    )

    rows = build_turnover_explanations(turnover, currency="EUR", source="ladder")
    assert [row["label"] for row in rows] == [
        "Max Turnover Price",
        "Max Turnover Index",
        "PI Source",
    ]
    assert rows[0]["value"] == "200.00 EUR"
    assert rows[2]["value"] == "PI ladder"
    assert "price ladder table" in rows[2]["explanation"]

    lines = build_turnover_summary(
        turnover,
        currency="EUR",
        segment_label="DE",
        source="ladder",
    )
    assert lines[0] == ("The highest turnover can be achieved by setting the price at 200.00 EUR.")
    assert any("turnover index reaches 100.00" in line for line in lines)
    assert any("PI source in this chart: PI ladder." in line for line in lines)


def test_describe_turnover_source_for_nms_fallback_is_explicit() -> None:
    label, note = describe_turnover_source("nms_trial")
    assert label == "NMS trial fallback"
    assert "NMS trial curve" in note


def test_build_profit_explanations_and_summary() -> None:
    profit = SimpleNamespace(unit_cost=75.0, max_profit_price=180.0, max_profit_index=100.0)

    rows = build_profit_explanations(profit, currency="EUR")
    assert [row["label"] for row in rows] == [
        "Unit Cost",
        "Max Profit Price",
        "Max Profit Index",
        "Break-even (Cost)",
    ]
    assert rows[0]["value"] == "75.00 EUR"
    assert rows[1]["value"] == "180.00 EUR"

    lines = build_profit_summary(
        profit,
        currency="EUR",
        segment_label="DE",
        product_label="Classic",
    )
    assert lines[0] == (
        "Given unit cost 75.00 EUR, the highest profit proxy is achieved at 180.00 EUR."
    )
    assert any("profit index reaches 100.00" in line for line in lines)
    assert any(
        "For Classic in DE, the break-even marker is set at 75.00 EUR." in line for line in lines
    )
    assert any("above break-even" in line for line in lines)
    assert any("Context: DE." in line for line in lines)
