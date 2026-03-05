from __future__ import annotations

import pandas as pd

from psm_tool.report.excel_export import _sanitize_excel_cell, _sanitize_excel_frame


def test_sanitize_excel_cell_prefixes_formula_like_strings() -> None:
    assert (
        _sanitize_excel_cell('=HYPERLINK("http://x", "click")')
        == '\'=HYPERLINK("http://x", "click")'
    )
    assert _sanitize_excel_cell("+cmd") == "'+cmd"
    assert _sanitize_excel_cell("-cmd") == "'-cmd"
    assert _sanitize_excel_cell("@cmd") == "'@cmd"
    assert _sanitize_excel_cell("safe") == "safe"


def test_sanitize_excel_frame_applies_to_all_string_cells() -> None:
    frame = pd.DataFrame(
        {
            "product_id": ['=HYPERLINK("http://x", "click")'],
            "segment": ["DE"],
            "value": [42.0],
        }
    )

    sanitized = _sanitize_excel_frame(frame)
    assert sanitized.loc[0, "product_id"].startswith("'=")
    assert sanitized.loc[0, "segment"] == "DE"
    assert sanitized.loc[0, "value"] == 42.0
