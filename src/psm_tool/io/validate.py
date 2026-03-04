from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

REQUIRED_COLUMNS = {
    "respondent_id",
    "segment",
    "currency",
    "too_cheap",
    "bargain",
    "expensive_acceptable",
    "too_expensive",
}
RECOMMENDED_COLUMNS = {"product_id"}
OPTIONAL_COLUMNS = {"weight", "puki", "pi_bargain_pct", "pi_expensive_pct"}
NUMERIC_COLUMNS = [
    "too_cheap",
    "bargain",
    "expensive_acceptable",
    "too_expensive",
    "weight",
    "puki",
    "pi_bargain_pct",
    "pi_expensive_pct",
]


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_df: pd.DataFrame


def canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {column: str(column).strip().lower() for column in df.columns}
    return df.rename(columns=renamed)


def template_columns() -> list[str]:
    return [
        "respondent_id",
        "segment",
        "currency",
        "product_id",
        "too_cheap",
        "bargain",
        "expensive_acceptable",
        "too_expensive",
        "weight",
        "puki",
        "pi_bargain_pct",
        "pi_expensive_pct",
    ]


def _coerce_numeric(df: pd.DataFrame, warnings: list[str]) -> None:
    for column in NUMERIC_COLUMNS:
        if column not in df.columns:
            continue
        original_missing = int(df[column].isna().sum())
        coerced = pd.to_numeric(df[column], errors="coerce")
        new_missing = int(coerced.isna().sum())
        newly_missing = max(new_missing - original_missing, 0)
        if newly_missing:
            warnings.append(
                f"Column '{column}' has {newly_missing} non-numeric values; coerced to missing."
            )
        df[column] = coerced.astype(float)


def _range_checks(df: pd.DataFrame, warnings: list[str]) -> None:
    if "weight" in df.columns:
        invalid_weight = int((df["weight"] <= 0).fillna(False).sum())
        if invalid_weight:
            warnings.append(
                f"Column 'weight' has {invalid_weight} non-positive values; "
                "they are ignored in weighted stats."
            )

    if "puki" in df.columns:
        invalid_puki = int((~df["puki"].isin([1, 2, 3, 4, 5])).fillna(False).sum())
        if invalid_puki:
            warnings.append(
                f"Column 'puki' has {invalid_puki} values outside 1..5; they are ignored."
            )

    for pi_col in ("pi_bargain_pct", "pi_expensive_pct"):
        if pi_col not in df.columns:
            continue
        invalid_pi = int(((df[pi_col] < 0) | (df[pi_col] > 100)).fillna(False).sum())
        if invalid_pi:
            warnings.append(
                f"Column '{pi_col}' has {invalid_pi} values outside 0..100; NMS clamps them."
            )


def validate_template(df: pd.DataFrame) -> ValidationResult:
    normalized = canonicalize_columns(df.copy())
    missing = sorted(REQUIRED_COLUMNS - set(normalized.columns))
    errors: list[str] = []
    warnings: list[str] = []

    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            normalized_df=normalized,
        )

    if "product_id" not in normalized.columns:
        warnings.append("Recommended column 'product_id' missing; defaulting to 'default_product'.")
        normalized["product_id"] = "default_product"

    _coerce_numeric(normalized, warnings)
    _range_checks(normalized, warnings)

    normalized["segment"] = normalized["segment"].astype(str)
    normalized["currency"] = normalized["currency"].astype(str)

    return ValidationResult(
        is_valid=True,
        errors=errors,
        warnings=warnings,
        normalized_df=normalized,
    )
