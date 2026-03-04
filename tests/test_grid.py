from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from psm_tool.config import GridConfig
from psm_tool.core.grid import build_price_grid_details


def _grid_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "too_cheap": [18, 20, 21],
            "bargain": [25, 28, 29],
            "expensive_acceptable": [34, 36, 37],
            "too_expensive": [42, 45, 47],
        }
    )


def test_auto_grid_snaps_for_known_currency() -> None:
    details = build_price_grid_details(_grid_df(), GridConfig(), currency="EUR")
    assert details.increment == 5.0
    assert details.snapped is True
    assert details.min_price == 15.0
    assert details.max_price == 50.0
    assert details.step % 5.0 == 0.0
    assert details.step >= 5.0
    assert np.isclose(details.prices[-1], 50.0)
    assert np.all(np.diff(details.prices) > 0)


def test_auto_grid_disables_snap_for_unknown_currency() -> None:
    details = build_price_grid_details(_grid_df(), GridConfig(), currency="USD")
    assert details.increment is None
    assert details.snapped is False
    assert details.min_price == 18.0
    assert details.max_price == 47.0


def test_manual_grid_requires_all_values() -> None:
    with pytest.raises(ValueError, match="Manual mode requires"):
        build_price_grid_details(_grid_df(), GridConfig(mode="manual"), currency="EUR")


def test_manual_grid_is_aligned_to_increment_when_snap_is_on() -> None:
    cfg = GridConfig(mode="manual", min_price=19, max_price=47, step=7)
    details = build_price_grid_details(_grid_df(), cfg, currency="EUR")
    assert details.min_price == 15.0
    assert details.max_price == 50.0
    assert details.step == 10.0
