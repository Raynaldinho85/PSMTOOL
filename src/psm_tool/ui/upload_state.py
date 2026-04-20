from __future__ import annotations

from collections.abc import Mapping, MutableMapping


def has_loaded_dataset(state: Mapping[str, object]) -> bool:
    return state.get("psm_input_df") is not None


def clear_loaded_dataset_state(state: MutableMapping[str, object]) -> None:
    state["psm_input_df"] = None
    state["psm_pi_ladder_df"] = None
    state["psm_analysis_payload"] = None
    state["psm_validation_errors"] = []
    state["psm_validation_warnings"] = []
    state["psm_input_source"] = None
    state["tested_price_by_key"] = {}
    state["tested_price_active_by_key"] = {}
