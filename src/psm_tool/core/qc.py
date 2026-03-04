from __future__ import annotations

import pandas as pd

ORDER_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]


def ordering_mask(df: pd.DataFrame) -> pd.Series:
    return (
        (df["too_cheap"] < df["bargain"])
        & (df["bargain"] < df["expensive_acceptable"])
        & (df["expensive_acceptable"] < df["too_expensive"])
    )


def qc_summary(df: pd.DataFrame) -> pd.DataFrame:
    valid_mask = ordering_mask(df.fillna(float("nan")))
    total_n = int(len(df))
    excluded_order = int((~valid_mask).sum())
    return pd.DataFrame(
        [
            {
                "total_n": total_n,
                "valid_n": total_n - excluded_order,
                "excluded_ordering_n": excluded_order,
            }
        ]
    )
