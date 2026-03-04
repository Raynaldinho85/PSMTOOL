from __future__ import annotations

from importlib import resources

import pandas as pd


def test_packaged_sample_dataset_loads_via_importlib_resources() -> None:
    with resources.files("psm_tool.resources").joinpath("sample_psm.csv").open("rb") as handle:
        df = pd.read_csv(handle)

    assert not df.empty
    assert len(df) >= 60
    assert {"segment", "currency", "pi_bargain_pct", "pi_expensive_pct"}.issubset(df.columns)
    assert {"DE", "SE", "CH"}.issubset(set(df["segment"].unique()))
    assert {"EUR", "SEK", "CHF"}.issubset(set(df["currency"].unique()))
