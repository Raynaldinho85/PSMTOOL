from __future__ import annotations

import pandas as pd

from psm_tool.core.qc import apply_psm_validity_filter, apply_puki_filter, compute_qc_report


def _qc_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "too_cheap": [10, 10, 10, 15],
            "bargain": [20, 20, None, 25],
            "expensive_acceptable": [30, 15, 30, 35],
            "too_expensive": [40, 30, 40, 45],
            "puki": [1, 3, 2, None],
        }
    )


def test_apply_psm_validity_filter_excludes_ordering_and_missing_rows() -> None:
    df_valid, mask = apply_psm_validity_filter(_qc_df())
    assert len(df_valid) == 2
    assert mask.tolist() == [True, False, False, True]


def test_compute_qc_report_contains_expected_counts() -> None:
    qc = compute_qc_report(_qc_df(), puki_threshold=2, apply_puki_filter=True)
    assert qc.total_n == 4
    assert qc.valid_psm_n == 2
    assert qc.excluded_ordering_n == 1
    assert qc.missing_any_threshold_n == 1
    assert qc.puki_filter_applied is True
    assert qc.puki_pass_n == 2
    assert qc.puki_excluded_n == 2


def test_compute_qc_report_handles_missing_puki_column() -> None:
    df = _qc_df().drop(columns=["puki"])
    qc = compute_qc_report(df, apply_puki_filter=True)
    assert qc.puki_filter_applied is False
    assert qc.puki_threshold is None
    assert qc.puki_pass_n is None


def test_apply_puki_filter_mixed_thresholds() -> None:
    df = pd.DataFrame({"puki": [2, 3], "value": ["strict", "neutral"]})

    strict, strict_mask = apply_puki_filter(df, puki_threshold=2)
    neutral, neutral_mask = apply_puki_filter(df, puki_threshold=3)

    assert strict["value"].tolist() == ["strict"]
    assert strict_mask.tolist() == [True, False]
    assert neutral["value"].tolist() == ["strict", "neutral"]
    assert neutral_mask.tolist() == [True, True]


def test_apply_puki_filter_only_twos_is_unchanged_by_threshold_three() -> None:
    df = pd.DataFrame({"puki": [1, 2], "value": [10, 20]})

    strict, _ = apply_puki_filter(df, puki_threshold=2)
    neutral, _ = apply_puki_filter(df, puki_threshold=3)

    assert strict["value"].tolist() == [10, 20]
    assert neutral["value"].tolist() == [10, 20]


def test_apply_puki_filter_only_threes_are_controlled_by_threshold() -> None:
    df = pd.DataFrame({"puki": [3, 3], "value": [10, 20]})

    strict, strict_mask = apply_puki_filter(df, puki_threshold=2)
    neutral, neutral_mask = apply_puki_filter(df, puki_threshold=3)

    assert strict.empty
    assert strict_mask.tolist() == [False, False]
    assert neutral["value"].tolist() == [10, 20]
    assert neutral_mask.tolist() == [True, True]


def test_apply_puki_filter_excludes_missing_and_non_numeric_values() -> None:
    df = pd.DataFrame({"puki": [2, None, "bad", 3], "value": [10, 20, 30, 40]})

    filtered, mask = apply_puki_filter(df, puki_threshold=3)

    assert filtered["value"].tolist() == [10, 40]
    assert mask.tolist() == [True, False, False, True]


def test_apply_puki_filter_missing_column_is_noop() -> None:
    df = pd.DataFrame({"value": [10, 20]})

    filtered, mask = apply_puki_filter(df, puki_threshold=2)

    assert filtered.equals(df)
    assert mask.tolist() == [True, True]
