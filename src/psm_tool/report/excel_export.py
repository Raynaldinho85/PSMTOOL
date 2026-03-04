from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


def _summary_frame(analyses: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for analysis in analyses:
        kpis = analysis["kpis"]
        outlier_settings = analysis.get("outlier_settings", {})
        outlier_stats = analysis.get("outlier_stats", {})
        rows.append(
            {
                "product_id": analysis["product_id"],
                "segment": analysis["segment"],
                "currency": analysis["currency"],
                "outlier_filter_applied": outlier_settings.get("enabled", False),
                "outlier_level": outlier_settings.get("level"),
                "outlier_excluded_n": outlier_stats.get("excluded_n", 0),
                "analysis_n_after_outlier": outlier_stats.get("analysis_n_after_outlier"),
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
        turnover_rows: list[pd.DataFrame] = []
        for analysis in analyses:
            nms_result = analysis.get("nms_result")
            turnover_result = analysis.get("turnover_index_result")
            if nms_result is None:
                if turnover_result is not None:
                    frame = turnover_result.df.copy()
                    frame.insert(0, "segment", analysis["segment"])
                    frame.insert(0, "product_id", analysis["product_id"])
                    turnover_rows.append(frame)
                continue
            row = {
                "product_id": analysis["product_id"],
                "segment": analysis["segment"],
                "currency": analysis["currency"],
                "max_trial_price": nms_result.max_trial_price,
                "max_revenue_price": nms_result.max_revenue_price,
            }
            if turnover_result is not None:
                row["max_turnover_price"] = turnover_result.max_turnover_price
                row["max_turnover_index"] = turnover_result.max_turnover_index
                frame = turnover_result.df.copy()
                frame.insert(0, "segment", analysis["segment"])
                frame.insert(0, "product_id", analysis["product_id"])
                turnover_rows.append(frame)
            nms_rows.append(row)
        if nms_rows:
            pd.DataFrame(nms_rows).to_excel(writer, sheet_name="nms_kpis", index=False)
        if turnover_rows:
            pd.concat(turnover_rows, ignore_index=True).to_excel(
                writer, sheet_name="turnover_index", index=False
            )

    return output.getvalue()
