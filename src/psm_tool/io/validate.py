from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from psm_tool.io.price_sanitization import sanitize_negative_price_columns

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
PRICE_THRESHOLD_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_df: pd.DataFrame


PI_UNIT_NORMALIZED_WARNING = (
    "PI unit normalized: detected fraction scale (0..1) and converted to percent (0..100)."
)
PI_CODE11_NORMALIZED_WARNING = (
    "PI unit normalized: detected coded scale (1..11) and converted to percent (0..100)."
)
PI_UNIT_TINY_WARNING = (
    "PI values look like fractions but are extremely small; not auto-scaled. Confirm units."
)
PI_UNIT_MIXED_ERROR = (
    "Mixed PI units detected: one PI column looks like fraction scale (0..1) while the other "
    "looks like percent scale (0..100). Please provide consistent units."
)


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


def detect_pi_unit_mode(values: pd.Series) -> Literal["percent", "fraction", "unknown"]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return "unknown"

    vmax = float(numeric.max())
    vmin = float(numeric.min())
    q95 = float(numeric.quantile(0.95))

    if vmax > 1.5 or q95 > 1.0:
        return "percent"
    if vmax <= 1.0 and vmin >= 0.0:
        return "fraction"
    return "unknown"


def detect_pi_code11_mode(values: pd.Series) -> bool:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return False
    within_bounds = bool(((numeric >= 1.0) & (numeric <= 11.0)).all())
    if not within_bounds:
        return False
    rounded = np.round(numeric.to_numpy(dtype=float))
    integer_like = bool(np.all(np.isclose(numeric.to_numpy(dtype=float), rounded, atol=1e-6)))
    return integer_like


def normalize_pi_code11_pair(
    df: pd.DataFrame,
    *,
    col_a: str = "pi_bargain_pct",
    col_b: str = "pi_expensive_pct",
) -> tuple[pd.DataFrame, str | None]:
    if col_a not in df.columns or col_b not in df.columns:
        return df, None

    out = df.copy()
    series_a = pd.to_numeric(out[col_a], errors="coerce")
    series_b = pd.to_numeric(out[col_b], errors="coerce")

    if not (detect_pi_code11_mode(series_a) and detect_pi_code11_mode(series_b)):
        return out, None

    combined = pd.concat([series_a, series_b], ignore_index=True).dropna()
    if combined.empty:
        return out, None

    has_strong_code_evidence = float(combined.max()) >= 10.0
    if not has_strong_code_evidence:
        return out, None

    out[col_a] = 10.0 + ((series_a - 1.0) * 9.0)
    out[col_b] = 10.0 + ((series_b - 1.0) * 9.0)
    return out, PI_CODE11_NORMALIZED_WARNING


def _fraction_strong_evidence(values: pd.Series) -> bool:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return False

    vmax = float(numeric.max())
    median = float(numeric.median())
    q95 = float(numeric.quantile(0.95))
    return (vmax >= 0.2) or (median >= 0.1) or (q95 >= 0.2)


def _fraction_is_tiny(values: pd.Series) -> bool:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return False
    return float(numeric.quantile(0.95)) < 0.05


def normalize_pi_pair_units(
    df: pd.DataFrame,
    *,
    col_a: str = "pi_bargain_pct",
    col_b: str = "pi_expensive_pct",
) -> tuple[pd.DataFrame, str | None]:
    if col_a not in df.columns or col_b not in df.columns:
        return df, None

    out = df.copy()
    series_a = pd.to_numeric(out[col_a], errors="coerce")
    series_b = pd.to_numeric(out[col_b], errors="coerce")

    mode_a = detect_pi_unit_mode(series_a)
    mode_b = detect_pi_unit_mode(series_b)

    mixed_units = (mode_a == "percent" and mode_b == "fraction") or (
        mode_a == "fraction" and mode_b == "percent"
    )
    if mixed_units:
        raise ValueError(PI_UNIT_MIXED_ERROR)

    if mode_a == "fraction" and mode_b == "fraction":
        combined = pd.concat([series_a, series_b], ignore_index=True)
        if _fraction_strong_evidence(combined):
            out[col_a] = series_a * 100.0
            out[col_b] = series_b * 100.0
            return out, PI_UNIT_NORMALIZED_WARNING
        if _fraction_is_tiny(combined):
            return out, PI_UNIT_TINY_WARNING

    return out, None


def normalize_single_pi_series(values: pd.Series) -> tuple[pd.Series, str | None]:
    numeric = pd.to_numeric(values, errors="coerce")
    mode = detect_pi_unit_mode(numeric)
    if mode == "fraction":
        if _fraction_strong_evidence(numeric):
            return numeric * 100.0, PI_UNIT_NORMALIZED_WARNING
        if _fraction_is_tiny(numeric):
            return numeric, PI_UNIT_TINY_WARNING
    return numeric, None


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
    normalized, negative_counts = sanitize_negative_price_columns(
        normalized, PRICE_THRESHOLD_COLUMNS
    )
    for column, count in negative_counts.items():
        if count > 0:
            warnings.append(f"Column '{column}' has {count} negative values; treated as missing.")
    try:
        normalized, pi_code11_note = normalize_pi_code11_pair(normalized)
        normalized, pi_unit_note = normalize_pi_pair_units(normalized)
    except ValueError as exc:
        errors.append(str(exc))
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            normalized_df=normalized,
        )
    if pi_code11_note is not None:
        warnings.append(pi_code11_note)
    if pi_unit_note is not None:
        warnings.append(pi_unit_note)
    _range_checks(normalized, warnings)

    normalized["segment"] = normalized["segment"].astype(str)
    normalized["currency"] = normalized["currency"].astype(str)

    return ValidationResult(
        is_valid=True,
        errors=errors,
        warnings=warnings,
        normalized_df=normalized,
    )
