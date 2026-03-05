from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _sanitize_excel_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def _sanitize_excel_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    sanitized = frame.copy()
    for column in sanitized.columns:
        if pd.api.types.is_object_dtype(sanitized[column]) or pd.api.types.is_string_dtype(
            sanitized[column]
        ):
            sanitized[column] = sanitized[column].map(_sanitize_excel_cell)
    return sanitized


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
        _sanitize_excel_frame(summary).to_excel(writer, sheet_name="kpis", index=False)
        _sanitize_excel_frame(curves).to_excel(writer, sheet_name="curves", index=False)
        nms_rows = []
        turnover_rows: list[pd.DataFrame] = []
        for analysis in analyses:
            nms_result = analysis.get("nms_result")
            turnover_result = analysis.get("turnover_index_result")
            profit_result = analysis.get("profit_proxy_result")
            unit_cost = analysis.get("unit_cost")
            row = {
                "product_id": analysis["product_id"],
                "segment": analysis["segment"],
                "currency": analysis["currency"],
                "max_trial_price": (nms_result.max_trial_price if nms_result is not None else None),
                "max_revenue_price": (
                    nms_result.max_revenue_price if nms_result is not None else None
                ),
                "unit_cost": unit_cost,
            }
            if turnover_result is not None:
                row["max_turnover_price"] = turnover_result.max_turnover_price
                row["max_turnover_index"] = turnover_result.max_turnover_index
                frame = turnover_result.df.copy()
                if profit_result is not None:
                    row["max_profit_price"] = profit_result.max_profit_price
                    row["max_profit_index"] = profit_result.max_profit_index
                    profit_frame = profit_result.df[
                        ["price", "profit_proxy_per_100", "profit_index"]
                    ]
                    frame = frame.merge(profit_frame, on="price", how="left")
                frame.insert(0, "segment", analysis["segment"])
                frame.insert(0, "product_id", analysis["product_id"])
                turnover_rows.append(frame)
            if nms_result is not None or turnover_result is not None or profit_result is not None:
                nms_rows.append(row)
        if nms_rows:
            _sanitize_excel_frame(pd.DataFrame(nms_rows)).to_excel(
                writer, sheet_name="nms_kpis", index=False
            )
        if turnover_rows:
            _sanitize_excel_frame(pd.concat(turnover_rows, ignore_index=True)).to_excel(
                writer,
                sheet_name="turnover_index",
                index=False,
            )

    return output.getvalue()
