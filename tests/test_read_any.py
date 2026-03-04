from __future__ import annotations

import importlib.util
from io import BytesIO

import pandas as pd
import pytest

from psm_tool.io.read_any import SAVDependencyError, read_any


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
