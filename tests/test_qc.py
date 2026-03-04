from __future__ import annotations

import pandas as pd

from psm_tool.core.qc import apply_psm_validity_filter, compute_qc_report


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
