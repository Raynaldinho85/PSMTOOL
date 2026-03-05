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


def test_validate_autoscales_fraction_pi_columns_to_percent() -> None:
    df = _valid_base_frame()
    df["pi_bargain_pct"] = [0.8]
    df["pi_expensive_pct"] = [0.6]

    result = validate_template(df)
    assert result.is_valid is True
    assert result.normalized_df["pi_bargain_pct"].iloc[0] == 80.0
    assert result.normalized_df["pi_expensive_pct"].iloc[0] == 60.0
    assert any("PI unit normalized" in warning for warning in result.warnings)


def test_validate_rejects_mixed_pi_units() -> None:
    df = _valid_base_frame()
    df["pi_bargain_pct"] = [0.8]
    df["pi_expensive_pct"] = [60.0]

    result = validate_template(df)
    assert result.is_valid is False
    assert any("Mixed PI units detected" in error for error in result.errors)


def test_validate_warns_for_tiny_fraction_like_pi_without_scaling() -> None:
    df = _valid_base_frame()
    df["pi_bargain_pct"] = [0.01]
    df["pi_expensive_pct"] = [0.02]

    result = validate_template(df)
    assert result.is_valid is True
    assert result.normalized_df["pi_bargain_pct"].iloc[0] == 0.01
    assert result.normalized_df["pi_expensive_pct"].iloc[0] == 0.02
    assert any("extremely small; not auto-scaled" in warning for warning in result.warnings)


def test_validate_maps_code11_pi_scale_to_percent() -> None:
    df = _valid_base_frame()
    df["pi_bargain_pct"] = [1]
    df["pi_expensive_pct"] = [11]

    result = validate_template(df)
    assert result.is_valid is True
    assert result.normalized_df["pi_bargain_pct"].iloc[0] == 10.0
    assert result.normalized_df["pi_expensive_pct"].iloc[0] == 100.0
    assert any("detected coded scale (1..11)" in warning for warning in result.warnings)


def test_validate_maps_full_code11_distribution_linearly() -> None:
    df = pd.DataFrame(
        {
            "respondent_id": ["A1", "A2", "A3"],
            "segment": ["DE", "DE", "DE"],
            "currency": ["EUR", "EUR", "EUR"],
            "too_cheap": [10, 10, 10],
            "bargain": [20, 20, 20],
            "expensive_acceptable": [30, 30, 30],
            "too_expensive": [40, 40, 40],
            "pi_bargain_pct": [1, 6, 11],
            "pi_expensive_pct": [2, 7, 10],
        }
    )
    result = validate_template(df)
    assert result.is_valid is True
    assert result.normalized_df["pi_bargain_pct"].tolist() == [10.0, 55.0, 100.0]
    assert result.normalized_df["pi_expensive_pct"].tolist() == [19.0, 64.0, 91.0]


def test_validate_does_not_autonormalize_non_clear_decimal_code11_like_values() -> None:
    df = _valid_base_frame()
    df["pi_bargain_pct"] = [1.5]
    df["pi_expensive_pct"] = [10.5]

    result = validate_template(df)
    assert result.is_valid is True
    assert result.normalized_df["pi_bargain_pct"].iloc[0] == 1.5
    assert result.normalized_df["pi_expensive_pct"].iloc[0] == 10.5
    assert not any("detected coded scale (1..11)" in warning for warning in result.warnings)


def test_validate_treats_negative_price_values_as_missing() -> None:
    df = _valid_base_frame()
    df["too_cheap"] = [-1]
    df["bargain"] = [20]
    result = validate_template(df)
    assert result.is_valid is True
    assert pd.isna(result.normalized_df["too_cheap"].iloc[0])
    assert any("negative values; treated as missing" in warning for warning in result.warnings)
