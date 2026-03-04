from __future__ import annotations

from io import BytesIO

import pandas as pd


def build_excel_report(summary: pd.DataFrame, curves: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        summary.to_excel(writer, sheet_name="kpis", index=False)
        curves.to_excel(writer, sheet_name="curves", index=False)
    return output.getvalue()
