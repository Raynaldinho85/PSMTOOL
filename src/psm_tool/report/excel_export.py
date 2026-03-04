from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


def _summary_frame(analyses: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for analysis in analyses:
        kpis = analysis["kpis"]
        rows.append(
            {
                "product_id": analysis["product_id"],
                "segment": analysis["segment"],
                "currency": analysis["currency"],
                **kpis,
            }
        )
    return pd.DataFrame(rows)


def _curves_frame(analyses: list[dict[str, Any]]) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for analysis in analyses:
        frame = analysis["curves"].copy()
        frame.insert(0, "segment", analysis["segment"])
        frame.insert(0, "product_id", analysis["product_id"])
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True)


def build_excel_report(report_payload: dict[str, Any]) -> bytes:
    analyses = report_payload.get("analyses", [])
    summary = _summary_frame(analyses)
    curves = _curves_frame(analyses)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        summary.to_excel(writer, sheet_name="kpis", index=False)
        curves.to_excel(writer, sheet_name="curves", index=False)
        nms_rows = []
        for analysis in analyses:
            nms_result = analysis.get("nms_result")
            if nms_result is None:
                continue
            row = {
                "product_id": analysis["product_id"],
                "segment": analysis["segment"],
                "currency": analysis["currency"],
                "max_trial_price": nms_result.max_trial_price,
                "max_revenue_price": nms_result.max_revenue_price,
            }
            nms_rows.append(row)
        if nms_rows:
            pd.DataFrame(nms_rows).to_excel(writer, sheet_name="nms_kpis", index=False)

    return output.getvalue()
