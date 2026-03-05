from __future__ import annotations

from importlib import resources

import pandas as pd


def test_packaged_sample_dataset_loads_via_importlib_resources() -> None:
    with resources.files("psm_tool.resources").joinpath("sample_psm.csv").open("rb") as handle:
        df = pd.read_csv(handle)

    assert not df.empty
    assert len(df) >= 3000
    assert {"segment", "currency", "pi_bargain_pct", "pi_expensive_pct"}.issubset(df.columns)
    assert {"product_id"}.issubset(df.columns)
    assert {"DE", "SE", "CH"}.issubset(set(df["segment"].unique()))
    assert {"EUR", "SEK", "CHF"}.issubset(set(df["currency"].unique()))
    combo_counts = df.groupby(["product_id", "segment"]).size()
    assert (combo_counts >= 500).all()
    pi_bargain = pd.to_numeric(df["pi_bargain_pct"], errors="coerce")
    pi_expensive = pd.to_numeric(df["pi_expensive_pct"], errors="coerce")
    pi_bargain_non_missing = pi_bargain.dropna()
    pi_expensive_non_missing = pi_expensive.dropna()
    assert len(pi_bargain_non_missing) > 0
    assert len(pi_expensive_non_missing) > 0
    assert pi_bargain_non_missing.between(1, 11).all()
    assert pi_expensive_non_missing.between(1, 11).all()
