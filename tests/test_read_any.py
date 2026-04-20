from __future__ import annotations

import importlib.util
from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from psm_tool.io.read_any import (
    SAVDependencyError,
    SAVUploadNotSupportedError,
    read_any,
    read_optional_pi_ladder,
    read_pi_ladder,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "respondent_id": [1, 2],
            "segment": ["DE", "SE"],
            "currency": ["EUR", "SEK"],
        }
    )


def test_read_any_csv_from_bytes() -> None:
    source = _frame()
    payload = source.to_csv(index=False).encode("utf-8")
    parsed = read_any(payload, filename="input.csv")
    pd.testing.assert_frame_equal(parsed, source)


def test_read_any_xlsx_from_bytes() -> None:
    source = _frame()
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        source.to_excel(writer, index=False)
    parsed = read_any(output.getvalue(), filename="input.xlsx")
    pd.testing.assert_frame_equal(parsed, source)


def test_read_any_sav_raises_dependency_error_when_pyreadstat_missing() -> None:
    if importlib.util.find_spec("pyreadstat") is not None:
        pytest.skip("pyreadstat is installed; missing-dependency scenario not applicable.")

    with pytest.raises(SAVDependencyError):
        read_any(b"dummy", filename="input.sav")


def test_read_any_sav_bytes_are_blocked_to_keep_uploads_in_memory() -> None:
    if importlib.util.find_spec("pyreadstat") is None:
        pytest.skip("pyreadstat missing; in-memory SAV guard only applies when SAV support exists.")

    with pytest.raises(SAVUploadNotSupportedError, match="processed fully in-memory"):
        read_any(b"dummy", filename="input.sav")


def test_read_pi_ladder_from_xlsx_sheet() -> None:
    ladder = pd.DataFrame(
        {
            "segment": ["DE"],
            "currency": ["eur"],
            "price": [200],
            "purchase_intention_pct": [75],
        }
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _frame().to_excel(writer, sheet_name="data", index=False)
        ladder.to_excel(writer, sheet_name="purchase_intention", index=False)

    parsed = read_pi_ladder(output.getvalue(), filename="input.xlsx")
    assert list(parsed.columns) == ["segment", "currency", "price", "purchase_intention_pct"]
    assert parsed["currency"].iloc[0] == "EUR"


def test_read_optional_pi_ladder_uses_suffix_for_csv() -> None:
    payload = (
        pd.DataFrame({"price": [100], "purchase_intention_pct": [20]})
        .to_csv(index=False)
        .encode("utf-8")
    )
    parsed = read_optional_pi_ladder(payload, filename="device_pi.csv")
    assert parsed is not None
    assert np.isclose(parsed["purchase_intention_pct"].iloc[0], 20.0)


def test_read_optional_pi_ladder_returns_none_for_regular_csv() -> None:
    payload = (
        pd.DataFrame({"price": [100], "purchase_intention_pct": [20]})
        .to_csv(index=False)
        .encode("utf-8")
    )
    parsed = read_optional_pi_ladder(payload, filename="device.csv")
    assert parsed is None


def test_read_pi_ladder_autoscales_fraction_values_and_sets_note() -> None:
    payload = (
        pd.DataFrame({"price": [100, 200], "purchase_intention_pct": [0.8, 0.6]})
        .to_csv(index=False)
        .encode("utf-8")
    )
    parsed = read_pi_ladder(payload, filename="device_pi.csv")
    assert np.allclose(parsed["purchase_intention_pct"].to_numpy(dtype=float), [80.0, 60.0])
    assert "PI unit normalized" in str(parsed.attrs.get("pi_unit_note", ""))


def test_read_pi_ladder_tiny_fraction_values_warn_without_scaling() -> None:
    payload = (
        pd.DataFrame({"price": [100, 200], "purchase_intention_pct": [0.01, 0.02]})
        .to_csv(index=False)
        .encode("utf-8")
    )
    parsed = read_pi_ladder(payload, filename="device_pi.csv")
    assert np.allclose(parsed["purchase_intention_pct"].to_numpy(dtype=float), [0.01, 0.02])
    assert "extremely small; not auto-scaled" in str(parsed.attrs.get("pi_unit_note", ""))


def test_read_pi_ladder_rejects_values_above_100() -> None:
    payload = (
        pd.DataFrame({"price": [100, 200], "purchase_intention_pct": [75, 120]})
        .to_csv(index=False)
        .encode("utf-8")
    )
    with pytest.raises(ValueError, match="must be in range 0..100"):
        read_pi_ladder(payload, filename="device_pi.csv")


def test_read_pi_ladder_treats_negative_prices_as_missing_rows() -> None:
    payload = (
        pd.DataFrame({"price": [-10, 100], "purchase_intention_pct": [70, 40]})
        .to_csv(index=False)
        .encode("utf-8")
    )
    parsed = read_pi_ladder(payload, filename="device_pi.csv")
    assert len(parsed) == 1
    assert float(parsed["price"].iloc[0]) == 100.0
    assert "Negative ladder prices treated as missing" in str(
        parsed.attrs.get("price_sanitization_note", "")
    )
