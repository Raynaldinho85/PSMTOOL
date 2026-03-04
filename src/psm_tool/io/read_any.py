from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd


def read_any(upload: bytes | BinaryIO | str | Path, filename: str | None = None) -> pd.DataFrame:
    """Read CSV/XLSX/SAV source into a dataframe.

    Full canonicalization and SAV handling are implemented in later milestones.
    """

    inferred_name = filename or (upload if isinstance(upload, (str, Path)) else "")
    suffix = Path(str(inferred_name)).suffix.lower()

    if isinstance(upload, (str, Path)):
        if suffix == ".csv":
            return pd.read_csv(upload)
        if suffix in {".xlsx", ".xlsm"}:
            return pd.read_excel(upload)
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")

    raw = upload.read() if hasattr(upload, "read") else upload
    if suffix == ".csv":
        return pd.read_csv(BytesIO(raw))
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(BytesIO(raw))
    if suffix == ".sav":
        raise RuntimeError(
            "SAV support requires optional dependency 'pyreadstat'. "
            "Install with: pip install 'psm-tool[sav]'"
        )
    raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")
