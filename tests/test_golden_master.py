from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.config import GridConfig
from psm_tool.core.curves import compute_psm_curves
from psm_tool.core.grid import build_price_grid_details
from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.qc import apply_psm_validity_filter
from psm_tool.io.validate import validate_template


def test_golden_master_psm_kpis_are_stable() -> None:
    df = pd.read_csv("tests/data/golden_master_psm.csv")
    validated = validate_template(df)
    assert validated.is_valid

    valid_df, _ = apply_psm_validity_filter(validated.normalized_df)
    grid = build_price_grid_details(valid_df, GridConfig(), currency="EUR")
    curves = compute_psm_curves(valid_df, grid.prices, weight_col="weight")
    kpis = compute_psm_kpis(curves)

    assert np.isclose(grid.min_price, 15.0)
    assert np.isclose(grid.max_price, 60.0)
    assert np.isclose(grid.step, 5.0)
    assert np.isclose(kpis.pmi.value, 26.35135135135135)
    assert np.isclose(kpis.opp.value, 30.0)
    assert np.isclose(kpis.idp.value, 35.0)
    assert np.isclose(kpis.pme.value, 45.0)
    assert np.isclose(kpis.accepted_low, 26.35135135135135)
    assert np.isclose(kpis.accepted_high, 45.0)
    assert np.isclose(kpis.price_stress, -5.0)
    assert kpis.stress_flag == "negative"
