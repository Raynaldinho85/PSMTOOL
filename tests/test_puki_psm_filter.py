from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.config import GridConfig
from psm_tool.core.curves import compute_psm_curves
from psm_tool.core.grid import build_price_grid_details
from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.qc import apply_psm_validity_filter, apply_puki_filter
from psm_tool.io.read_any import read_any
from psm_tool.io.validate import validate_template


def _uploaded_style_dataset() -> pd.DataFrame:
    rows = [
        {
            "respondent_id": "a",
            "segment": "DE",
            "currency": "EUR",
            "product_id": "X",
            "too_cheap": 10,
            "bargain": 20,
            "expensive_acceptable": 30,
            "too_expensive": 40,
            "PUKI": "2",
            "pi_bargain_pct": 80,
            "pi_expensive_pct": 40,
        },
        {
            "respondent_id": "b",
            "segment": "DE",
            "currency": "EUR",
            "product_id": "X",
            "too_cheap": 12,
            "bargain": 22,
            "expensive_acceptable": 32,
            "too_expensive": 42,
            "PUKI": "2",
            "pi_bargain_pct": 75,
            "pi_expensive_pct": 35,
        },
        {
            "respondent_id": "c",
            "segment": "DE",
            "currency": "EUR",
            "product_id": "X",
            "too_cheap": 30,
            "bargain": 50,
            "expensive_acceptable": 70,
            "too_expensive": 90,
            "PUKI": "3",
            "pi_bargain_pct": 90,
            "pi_expensive_pct": 80,
        },
        {
            "respondent_id": "d",
            "segment": "DE",
            "currency": "EUR",
            "product_id": "X",
            "too_cheap": 32,
            "bargain": 52,
            "expensive_acceptable": 72,
            "too_expensive": 92,
            "PUKI": "3",
            "pi_bargain_pct": 95,
            "pi_expensive_pct": 85,
        },
    ]
    raw = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    parsed = read_any(raw, filename="uploaded_puki_psm.csv")
    result = validate_template(parsed)
    assert result.is_valid
    return result.normalized_df


def _psm_curves_for_threshold(df: pd.DataFrame, threshold: int) -> pd.DataFrame:
    valid_df, _valid_mask = apply_psm_validity_filter(df)
    analysis_df, _puki_mask = apply_puki_filter(valid_df, puki_threshold=threshold)
    grid = build_price_grid_details(
        analysis_df,
        GridConfig(mode="manual", snap_enabled=False, min_price=10, max_price=95, step=5),
        currency="EUR",
    )
    return compute_psm_curves(analysis_df, grid.prices)


def test_uploaded_puki_threshold_changes_psm_curves_and_kpis() -> None:
    df = _uploaded_style_dataset()

    strict_curves = _psm_curves_for_threshold(df, 2)
    neutral_curves = _psm_curves_for_threshold(df, 3)
    strict_kpis = compute_psm_kpis(strict_curves).as_dict()
    neutral_kpis = compute_psm_kpis(neutral_curves).as_dict()

    strict_too_cheap_at_30 = strict_curves.loc[
        np.isclose(strict_curves["price"], 30.0), "too_cheap"
    ].iloc[0]
    neutral_too_cheap_at_30 = neutral_curves.loc[
        np.isclose(neutral_curves["price"], 30.0), "too_cheap"
    ].iloc[0]

    assert strict_too_cheap_at_30 == 0.0
    assert neutral_too_cheap_at_30 == 50.0
    assert strict_kpis["opp"] != neutral_kpis["opp"]
