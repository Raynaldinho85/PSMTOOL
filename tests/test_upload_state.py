from __future__ import annotations

import pandas as pd

from psm_tool.ui.upload_state import clear_loaded_dataset_state, has_loaded_dataset


def test_has_loaded_dataset_detects_presence() -> None:
    empty_state: dict[str, object] = {"psm_input_df": None}
    loaded_state: dict[str, object] = {"psm_input_df": pd.DataFrame({"x": [1]})}

    assert has_loaded_dataset(empty_state) is False
    assert has_loaded_dataset(loaded_state) is True


def test_clear_loaded_dataset_state_resets_relevant_session_keys() -> None:
    state: dict[str, object] = {
        "psm_input_df": pd.DataFrame({"x": [1]}),
        "psm_pi_ladder_df": pd.DataFrame({"price": [100]}),
        "psm_analysis_payload": {"kpi": 1},
        "psm_validation_errors": ["err"],
        "psm_validation_warnings": ["warn"],
        "psm_input_source": "file.csv",
        "tested_price_by_key": {"Classic::DE": 20.0},
        "tested_price_active_by_key": {"Classic::DE": True},
    }

    clear_loaded_dataset_state(state)

    assert state["psm_input_df"] is None
    assert state["psm_pi_ladder_df"] is None
    assert state["psm_analysis_payload"] is None
    assert state["psm_validation_errors"] == []
    assert state["psm_validation_warnings"] == []
    assert state["psm_input_source"] is None
    assert state["tested_price_by_key"] == {}
    assert state["tested_price_active_by_key"] == {}
