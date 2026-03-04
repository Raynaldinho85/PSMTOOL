from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd


class SAVDependencyError(RuntimeError):
    """Raised when SAV support is requested without optional dependency."""


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
            "Install with: pip install 'psm-tool[sav]'"
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
