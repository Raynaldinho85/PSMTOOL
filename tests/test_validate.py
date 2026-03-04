from __future__ import annotations

import pandas as pd

from psm_tool.io.validate import validate_template


def _valid_base_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "respondent_id": ["A1"],
            "segment": ["DE"],
            "currency": ["EUR"],
            "too_cheap": [10],
            "bargain": [20],
            "expensive_acceptable": [30],
            "too_expensive": [40],
        }
    )


def test_validate_fails_when_required_columns_missing() -> None:
    df = pd.DataFrame({"respondent_id": ["A1"], "segment": ["DE"]})
    result = validate_template(df)
    assert result.is_valid is False
    assert "Missing required columns" in result.errors[0]


def test_validate_adds_default_product_id_when_missing() -> None:
    result = validate_template(_valid_base_frame())
    assert result.is_valid is True
    assert "product_id" in result.normalized_df.columns
    assert result.normalized_df["product_id"].iloc[0] == "default_product"


def test_validate_normalizes_columns_and_coerces_numeric_values() -> None:
    df = pd.DataFrame(
        {
            "Respondent_ID": ["A1"],
            "Segment": ["DE"],
            "Currency": ["EUR"],
            "Too_Cheap": ["10"],
            "BARGAIN": ["bad"],
            "Expensive_Acceptable": [30],
            "Too_Expensive": [40],
            "weight": ["0"],
            "puki": [6],
        }
    )
    result = validate_template(df)
    out = result.normalized_df

    assert result.is_valid is True
    assert pd.isna(out["bargain"].iloc[0])
    assert out["too_cheap"].iloc[0] == 10.0
    assert any("non-numeric values" in warning for warning in result.warnings)
    assert any("non-positive values" in warning for warning in result.warnings)
    assert any("outside 1..5" in warning for warning in result.warnings)
