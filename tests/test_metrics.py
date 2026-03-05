from __future__ import annotations

import numpy as np
import pandas as pd

from psm_tool.core.metrics import compute_psm_kpis


def test_compute_psm_kpis_returns_expected_core_values() -> None:
    curves = pd.DataFrame(
        {
            "price": np.array([10.0, 20.0, 30.0, 40.0, 50.0]),
            "too_cheap": np.array([100.0, 80.0, 60.0, 40.0, 20.0]),
            "bargain": np.array([100.0, 90.0, 70.0, 40.0, 10.0]),
            "expensive": np.array([0.0, 10.0, 30.0, 60.0, 90.0]),
            "too_expensive": np.array([0.0, 20.0, 40.0, 60.0, 80.0]),
            "not_bargain": np.array([0.0, 10.0, 30.0, 60.0, 90.0]),
            "not_expensive": np.array([100.0, 90.0, 70.0, 40.0, 10.0]),
        }
    )
    kpis = compute_psm_kpis(curves)

    assert np.isclose(kpis.opp.value, 35.0)
    assert np.isclose(kpis.idp.value, 36.6666666667)
    assert np.isclose(kpis.pmi.value, 36.0)
    assert np.isclose(kpis.pme.value, 36.0)
    assert np.isclose(kpis.accepted_low, 36.0)
    assert np.isclose(kpis.accepted_high, 36.0)
    assert np.isclose(kpis.price_stress, -1.6666666667)
    assert kpis.stress_flag == "negative"


def test_psm_kpi_dict_exposes_interval_bounds_and_unstable_flag() -> None:
    curves = pd.DataFrame(
        {
            "price": np.array([10.0, 20.0, 30.0]),
            "too_cheap": np.array([50.0, 50.0, 40.0]),
            "bargain": np.array([70.0, 60.0, 30.0]),
            "expensive": np.array([20.0, 50.0, 80.0]),
            "too_expensive": np.array([50.0, 50.0, 60.0]),
            "not_bargain": np.array([30.0, 40.0, 70.0]),
            "not_expensive": np.array([80.0, 50.0, 20.0]),
        }
    )
    kpi_dict = compute_psm_kpis(curves).as_dict()
    assert kpi_dict["opp_status"] == "interval"
    assert np.isclose(float(kpi_dict["opp_low"]), 10.0)
    assert np.isclose(float(kpi_dict["opp_high"]), 20.0)
    assert bool(kpi_dict["has_unstable_intersections"]) is True
