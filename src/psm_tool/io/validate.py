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


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_df: pd.DataFrame


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {column: str(column).strip().lower() for column in df.columns}
    return df.rename(columns=renamed)


def validate_template(df: pd.DataFrame) -> ValidationResult:
    normalized = _normalize_columns(df.copy())
    missing = sorted(REQUIRED_COLUMNS - set(normalized.columns))
    errors: list[str] = []
    warnings: list[str] = []
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")

    if "product_id" not in normalized.columns:
        warnings.append("Recommended column 'product_id' missing; defaulting to 'default_product'.")
        normalized["product_id"] = "default_product"

    return ValidationResult(
        is_valid=not errors, errors=errors, warnings=warnings, normalized_df=normalized
    )
