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
