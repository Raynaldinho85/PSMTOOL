from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from psm_tool.io.validate import normalize_single_pi_series


class SAVDependencyError(RuntimeError):
    """Raised when SAV support is requested without optional dependency."""


PI_LADDER_REQUIRED_COLUMNS = ["price", "purchase_intention_pct"]
PI_LADDER_OPTIONAL_COLUMNS = ["segment", "currency", "product_id"]


def _to_bytes(upload: bytes | BinaryIO) -> bytes:
    if isinstance(upload, bytes):
        return upload
    return upload.read()


def _read_sav_bytes(raw: bytes) -> pd.DataFrame:
    try:
        import pyreadstat  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised in dedicated test later
        raise SAVDependencyError(
            "SAV support requires optional dependency 'pyreadstat'. "
            "Install in this repo with: pip install -e .[sav] "
            '(or from package index: pip install "psm-tool[sav]").'
        ) from exc

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".sav",
            prefix=".tmp_sav_",
            dir=Path.cwd(),
            delete=False,
        ) as handle:
            handle.write(raw)
            handle.flush()
            temp_path = Path(handle.name)
        df, _meta = pyreadstat.read_sav(str(temp_path))
        return df
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


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
            "Purchase intention ladder missing required columns: "
            + ", ".join(PI_LADDER_REQUIRED_COLUMNS)
        )

    out = renamed.copy()
    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out["purchase_intention_pct"] = pd.to_numeric(out["purchase_intention_pct"], errors="coerce")
    out = out.dropna(subset=["price", "purchase_intention_pct"]).copy()

    lower_bound_violation = bool((out["purchase_intention_pct"] < 0.0).any())
    upper_bound_violation = bool((out["purchase_intention_pct"] > 100.0).any())
    if lower_bound_violation or upper_bound_violation:
        raise ValueError(
            "Purchase intention ladder values must be in range 0..100 (percent) or "
            "0..1 (fraction scale)."
        )

    normalized_series, pi_unit_note = normalize_single_pi_series(out["purchase_intention_pct"])
    out["purchase_intention_pct"] = normalized_series
    if bool((out["purchase_intention_pct"] > 100.0).any()):
        raise ValueError(
            "Purchase intention ladder values exceed 100 after normalization. "
            "Please verify PI units."
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
            raise ValueError("PI ladder only supports CSV and XLSX files.")
        return _canonicalize_pi_ladder(frame)

    raw = _to_bytes(upload)
    if suffix == ".csv":
        frame = pd.read_csv(BytesIO(raw))
        return _canonicalize_pi_ladder(frame)
    if suffix in {".xlsx", ".xlsm"}:
        frame = pd.read_excel(BytesIO(raw), sheet_name="purchase_intention")
        return _canonicalize_pi_ladder(frame)
    raise ValueError("PI ladder only supports CSV and XLSX files.")


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
            return _read_sav_bytes(path.read_bytes())
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")

    raw = _to_bytes(upload)
    if suffix == ".csv":
        return pd.read_csv(BytesIO(raw))
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(BytesIO(raw))
    if suffix == ".sav":
        return _read_sav_bytes(raw)
    raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")
