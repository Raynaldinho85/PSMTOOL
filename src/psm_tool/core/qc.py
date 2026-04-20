from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

PRICE_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]


@dataclass(slots=True)
class QCResult:
    total_n: int
    valid_psm_n: int
    excluded_ordering_n: int
    missing_any_threshold_n: int
    missing_too_cheap_n: int
    missing_bargain_n: int
    missing_expensive_acceptable_n: int
    missing_too_expensive_n: int
    puki_filter_applied: bool
    puki_threshold: int | None
    puki_pass_n: int | None
    puki_excluded_n: int | None

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(self)])


def ordering_mask(df: pd.DataFrame) -> pd.Series:
    complete = df[PRICE_COLUMNS].notna().all(axis=1)
    ordered = (
        (df["too_cheap"] < df["bargain"])
        & (df["bargain"] < df["expensive_acceptable"])
        & (df["expensive_acceptable"] < df["too_expensive"])
    )
    return complete & ordered


def apply_psm_validity_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    mask = ordering_mask(df)
    return df.loc[mask].copy(), mask


def puki_eligibility_mask(df: pd.DataFrame, *, puki_threshold: int) -> pd.Series:
    if "puki" not in df.columns:
        return pd.Series(True, index=df.index, dtype=bool)
    puki_numeric = pd.to_numeric(df["puki"], errors="coerce")
    return puki_numeric.le(float(puki_threshold)).fillna(False)


def apply_puki_filter(
    df: pd.DataFrame,
    *,
    puki_threshold: int,
    enabled: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    if not enabled or "puki" not in df.columns:
        mask = pd.Series(True, index=df.index, dtype=bool)
        return df.copy(), mask
    mask = puki_eligibility_mask(df, puki_threshold=puki_threshold)
    return df.loc[mask].copy(), mask


def compute_qc_report(
    df: pd.DataFrame,
    *,
    puki_threshold: int = 2,
    apply_puki_filter: bool = True,
) -> QCResult:
    valid_mask = ordering_mask(df)
    missing_any = df[PRICE_COLUMNS].isna().any(axis=1)

    puki_filter_applied = apply_puki_filter and ("puki" in df.columns)
    puki_pass_n: int | None = None
    puki_excluded_n: int | None = None
    threshold_out: int | None = None
    if puki_filter_applied:
        threshold_out = puki_threshold
        pass_mask = puki_eligibility_mask(df, puki_threshold=puki_threshold)
        puki_pass_n = int(pass_mask.fillna(False).sum())
        puki_excluded_n = int((~pass_mask.fillna(False)).sum())

    return QCResult(
        total_n=int(len(df)),
        valid_psm_n=int(valid_mask.sum()),
        excluded_ordering_n=int((~valid_mask & ~missing_any).sum()),
        missing_any_threshold_n=int(missing_any.sum()),
        missing_too_cheap_n=int(df["too_cheap"].isna().sum()),
        missing_bargain_n=int(df["bargain"].isna().sum()),
        missing_expensive_acceptable_n=int(df["expensive_acceptable"].isna().sum()),
        missing_too_expensive_n=int(df["too_expensive"].isna().sum()),
        puki_filter_applied=puki_filter_applied,
        puki_threshold=threshold_out,
        puki_pass_n=puki_pass_n,
        puki_excluded_n=puki_excluded_n,
    )
