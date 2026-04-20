from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from psm_tool.i18n.runtime import tr
from psm_tool.io.price_sanitization import sanitize_negative_price_columns
from psm_tool.io.validate import normalize_single_pi_series


class SAVDependencyError(RuntimeError):
    """Raised when SAV support is requested without optional dependency."""


class SAVUploadNotSupportedError(RuntimeError):
    """Raised when SAV uploads would violate the in-memory processing guardrail."""


PI_LADDER_REQUIRED_COLUMNS = ["price", "purchase_intention_pct"]
PI_LADDER_OPTIONAL_COLUMNS = ["segment", "currency", "product_id"]


def _to_bytes(upload: bytes | BinaryIO) -> bytes:
    if isinstance(upload, bytes):
        return upload
    return upload.read()


def _read_sav_path(path: str | Path) -> pd.DataFrame:
    try:
        import pyreadstat  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised in dedicated test later
        raise SAVDependencyError(
            tr(
                (
                    "SAV support requires optional dependency 'pyreadstat'. "
                    "Install in this repo with: pip install -e .[sav] (or "
                    'from package index: pip install "psm-tool[sav]").'
                ),
                None,
            )
        ) from exc

    df, _meta = pyreadstat.read_sav(str(path))
    return df


def _raise_sav_upload_not_supported() -> None:
    raise SAVUploadNotSupportedError(
        tr(
            (
                "SAV uploads are disabled in the app because uploaded files must be "
                "processed fully in-memory. Please convert SAV to CSV or XLSX first."
            ),
            None,
        )
    )


def _canonicalize_pi_ladder(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(
        columns={
            "Purchase_Intention_Pct": "purchase_intention_pct",
            "purchase_intention": "purchase_intention_pct",
            "pi_pct": "purchase_intention_pct",
            "Product_ID": "product_id",
            "Segment": "segment",
            "Currency": "currency",
            "Price": "price",
        }
    )
    missing = [col for col in PI_LADDER_REQUIRED_COLUMNS if col not in renamed.columns]
    if missing:
        raise ValueError(
            tr(
                "Purchase intention ladder missing required columns: {required_columns}",
                None,
                required_columns=", ".join(PI_LADDER_REQUIRED_COLUMNS),
            )
        )

    out = renamed.copy()
    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out["purchase_intention_pct"] = pd.to_numeric(out["purchase_intention_pct"], errors="coerce")
    out, negative_price_counts = sanitize_negative_price_columns(out, ["price"])
    out = out.dropna(subset=["price", "purchase_intention_pct"]).copy()

    lower_bound_violation = bool((out["purchase_intention_pct"] < 0.0).any())
    upper_bound_violation = bool((out["purchase_intention_pct"] > 100.0).any())
    if lower_bound_violation or upper_bound_violation:
        raise ValueError(
            tr(
                (
                    "Purchase intention ladder values must be in range 0..100 "
                    "(percent) or 0..1 (fraction scale)."
                ),
                None,
            )
        )

    normalized_series, pi_unit_note = normalize_single_pi_series(out["purchase_intention_pct"])
    out["purchase_intention_pct"] = normalized_series
    if bool((out["purchase_intention_pct"] > 100.0).any()):
        raise ValueError(
            tr(
                (
                    "Purchase intention ladder values exceed 100 after "
                    "normalization. Please verify PI units."
                ),
                None,
            )
        )

    keep_cols = [col for col in PI_LADDER_OPTIONAL_COLUMNS if col in out.columns]
    keep_cols.extend(PI_LADDER_REQUIRED_COLUMNS)
    out = out[keep_cols].reset_index(drop=True)
    if "currency" in out.columns:
        out["currency"] = out["currency"].astype(str).str.upper()
    if "segment" in out.columns:
        out["segment"] = out["segment"].astype(str)
    if "product_id" in out.columns:
        out["product_id"] = out["product_id"].astype(str)
    if pi_unit_note:
        out.attrs["pi_unit_note"] = pi_unit_note
    negative_price_count = int(negative_price_counts.get("price", 0))
    if negative_price_count > 0:
        out.attrs["price_sanitization_note"] = tr(
            "Negative ladder prices treated as missing: {negative_price_count} rows.",
            None,
            negative_price_count=negative_price_count,
        )
    return out


def read_pi_ladder(
    upload: bytes | BinaryIO | str | Path, filename: str | None = None
) -> pd.DataFrame:
    inferred_name = filename or (str(upload) if isinstance(upload, (str, Path)) else "")
    suffix = Path(inferred_name).suffix.lower()

    if isinstance(upload, (str, Path)):
        path = Path(upload)
        if suffix == ".csv":
            frame = pd.read_csv(path)
        elif suffix in {".xlsx", ".xlsm"}:
            frame = pd.read_excel(path, sheet_name="purchase_intention")
        else:
            raise ValueError(tr("PI ladder only supports CSV and XLSX files.", None))
        return _canonicalize_pi_ladder(frame)

    raw = _to_bytes(upload)
    if suffix == ".csv":
        frame = pd.read_csv(BytesIO(raw))
        return _canonicalize_pi_ladder(frame)
    if suffix in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(BytesIO(raw), sheet_name="purchase_intention")
        return _canonicalize_pi_ladder(frame)
    raise ValueError(tr("PI ladder only supports CSV and XLSX files.", None))


def read_optional_pi_ladder(
    upload: bytes | BinaryIO | str | Path,
    filename: str | None = None,
) -> pd.DataFrame | None:
    inferred_name = filename or (str(upload) if isinstance(upload, (str, Path)) else "")
    lower_name = inferred_name.lower()
    suffix = Path(lower_name).suffix

    if suffix in {".xlsx", ".xlsm"}:
        try:
            return read_pi_ladder(upload, filename=inferred_name)
        except ValueError as exc:
            if "Worksheet named" in str(exc) and "purchase_intention" in str(exc):
                return None
            raise
    if suffix == ".csv" and lower_name.endswith("_pi.csv"):
        return read_pi_ladder(upload, filename=inferred_name)
    return None


def read_any(upload: bytes | BinaryIO | str | Path, filename: str | None = None) -> pd.DataFrame:
    inferred_name = filename or (str(upload) if isinstance(upload, (str, Path)) else "")
    suffix = Path(inferred_name).suffix.lower()

    if isinstance(upload, (str, Path)):
        path = Path(upload)
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in {".xlsx", ".xlsm"}:
            return pd.read_excel(path)
        if suffix == ".sav":
            return _read_sav_path(path)
        raise ValueError(
            tr(
                "Unsupported file type: {suffix}",
                None,
                suffix=suffix or "unknown",
            )
        )

    raw = _to_bytes(upload)
    if suffix == ".csv":
        return pd.read_csv(BytesIO(raw))
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(BytesIO(raw))
    if suffix == ".sav":
        _raise_sav_upload_not_supported()
    raise ValueError(
        tr(
            "Unsupported file type: {suffix}",
            None,
            suffix=suffix or "unknown",
        )
    )
