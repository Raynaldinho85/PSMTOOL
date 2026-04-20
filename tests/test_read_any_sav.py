from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pandas as pd
import pytest

from psm_tool.io.read_any import SAVUploadNotSupportedError, read_any

pytestmark = pytest.mark.sav


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "respondent_id": [1, 2],
            "segment": ["DE", "SE"],
            "currency": ["EUR", "SEK"],
            "too_cheap": [10.0, 100.0],
            "bargain": [20.0, 120.0],
            "expensive_acceptable": [30.0, 140.0],
            "too_expensive": [40.0, 160.0],
        }
    )


def _local_tmp_dir() -> Path:
    path = Path(".tmp_test_sav") / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_read_any_reads_sav_from_path() -> None:
    pyreadstat = pytest.importorskip("pyreadstat")
    temp_dir = _local_tmp_dir()
    try:
        source = _sample_df()
        sav_path = temp_dir / "sample.sav"
        pyreadstat.write_sav(source, str(sav_path))

        loaded = read_any(sav_path)
        assert set(source.columns) == set(loaded.columns)
        assert len(loaded) == len(source)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_read_any_blocks_sav_from_bytes() -> None:
    pyreadstat = pytest.importorskip("pyreadstat")
    temp_dir = _local_tmp_dir()
    try:
        source = _sample_df()
        sav_path = temp_dir / "sample_bytes.sav"
        pyreadstat.write_sav(source, str(sav_path))

        payload = sav_path.read_bytes()
        with pytest.raises(SAVUploadNotSupportedError, match="processed fully in-memory"):
            read_any(payload, filename="uploaded.sav")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
