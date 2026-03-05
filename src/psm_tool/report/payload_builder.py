from __future__ import annotations

from typing import Any

import pandas as pd

from psm_tool.config import GridConfig
from psm_tool.core.curves import compute_psm_curves
from psm_tool.core.grid import build_price_grid_details
from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.core.nms import compute_nms
from psm_tool.core.outliers import apply_outlier_filter
from psm_tool.core.qc import apply_psm_validity_filter
from psm_tool.core.turnover_index import (
    compute_profit_proxy,
    compute_turnover_index,
    resolve_purchase_intention_curve,
)

PRICE_COLUMNS = ["too_cheap", "bargain", "expensive_acceptable", "too_expensive"]


def _series_or_default(df: pd.DataFrame, column: str, default: str) -> pd.Series:
    if column in df.columns:
        return df[column].fillna(default).astype(str)
    return pd.Series([default] * len(df), index=df.index)


def _weight_column(df: pd.DataFrame) -> str | None:
    return "weight" if "weight" in df.columns else None


def _has_nms_columns(df: pd.DataFrame) -> bool:
    required = {"pi_bargain_pct", "pi_expensive_pct"}
    return required.issubset(df.columns)


def _cost_key(product_id: str, segment: str) -> str:
    product = str(product_id).strip()
    if product:
        return product
    return f"segment::{segment}"


def _select_pi_ladder_for_group(
    pi_ladder_df: pd.DataFrame | None,
    *,
    segment: str,
    currency: str,
    product_id: str,
) -> pd.DataFrame | None:
    if pi_ladder_df is None or len(pi_ladder_df) == 0:
        return None
    selected = pi_ladder_df.copy()
    if "segment" in selected.columns:
        selected = selected.loc[selected["segment"].astype(str) == str(segment)]
    if "currency" in selected.columns:
        selected = selected.loc[
            selected["currency"].astype(str).str.upper() == str(currency).upper()
        ]
    if "product_id" in selected.columns:
        selected = selected.loc[selected["product_id"].astype(str) == str(product_id)]
    if len(selected) == 0:
        return None
    return selected


def build_export_payload_from_dataset(
    df: pd.DataFrame,
    *,
    pi_ladder_df: pd.DataFrame | None = None,
    plausibility_filter_applied: bool = True,
    outlier_enabled: bool = False,
    outlier_level: str = "medium",
    puki_threshold: int = 2,
    snap_enabled: bool = True,
    unit_cost_by_key: dict[str, float] | None = None,
    economics_enabled_by_key: dict[str, bool] | None = None,
) -> dict[str, Any]:
    analyses: list[dict[str, Any]] = []
    unit_cost_map = unit_cost_by_key or {}
    economics_map = economics_enabled_by_key or {}

    product_values = sorted(_series_or_default(df, "product_id", "default_product").unique())
    for product in product_values:
        product_df = df.loc[
            _series_or_default(df, "product_id", "default_product") == product
        ].copy()
        segment_values = sorted(
            _series_or_default(product_df, "segment", "default_segment").unique()
        )
        for segment in segment_values:
            group_df = product_df.loc[
                _series_or_default(product_df, "segment", "default_segment") == segment
            ].copy()
            if len(group_df) == 0:
                continue

            currency = str(_series_or_default(group_df, "currency", "").iloc[0]).upper()
            valid_df, _valid_mask = apply_psm_validity_filter(group_df)
            analysis_base_df = valid_df if plausibility_filter_applied else group_df.copy()
            outlier_result = apply_outlier_filter(
                analysis_base_df,
                columns=PRICE_COLUMNS,
                level=str(outlier_level),
                enabled=bool(outlier_enabled),
            )
            analysis_df = outlier_result.filtered_df
            if len(analysis_df) == 0:
                continue

            grid_cfg = GridConfig(mode="auto", snap_enabled=bool(snap_enabled))
            try:
                grid_details = build_price_grid_details(analysis_df, grid_cfg, currency=currency)
            except ValueError:
                continue

            weight_col = _weight_column(analysis_df)
            curves = compute_psm_curves(analysis_df, grid_details.prices, weight_col=weight_col)
            kpi_result = compute_psm_kpis(curves)
            kpis = kpi_result.as_dict()

            nms_result = None
            if _has_nms_columns(analysis_df):
                nms_result = compute_nms(
                    analysis_df,
                    grid_details.prices,
                    weight_col=weight_col,
                    puki_threshold=int(puki_threshold),
                )

            selected_ladder = _select_pi_ladder_for_group(
                pi_ladder_df,
                segment=str(segment),
                currency=currency,
                product_id=str(product),
            )
            turnover_result = None
            turnover_source: str | None = None
            try:
                pi_curve, turnover_source = resolve_purchase_intention_curve(
                    grid_details.prices,
                    pi_ladder_df=selected_ladder,
                    nms_curves=(nms_result.curves if nms_result is not None else None),
                )
                turnover_result = compute_turnover_index(grid_details.prices, pi_curve)
            except ValueError:
                turnover_result = None
                turnover_source = None

            cost_key = _cost_key(str(product), str(segment))
            unit_cost: float | None = None
            if bool(economics_map.get(cost_key, False)):
                if cost_key in unit_cost_map:
                    unit_cost = float(unit_cost_map[cost_key])

            profit_result = None
            if turnover_result is not None and unit_cost is not None:
                profit_result = compute_profit_proxy(
                    grid_details.prices,
                    turnover_result.df["purchase_intention_pct"].to_numpy(dtype=float),
                    float(unit_cost),
                )

            analyses.append(
                {
                    "product_id": str(product),
                    "segment": str(segment),
                    "currency": currency,
                    "curves": curves,
                    "kpis": kpis,
                    "kpi_result": kpi_result,
                    "nms_result": nms_result,
                    "turnover_index_result": turnover_result,
                    "profit_proxy_result": profit_result,
                    "turnover_source": turnover_source,
                    "unit_cost": unit_cost,
                    "outlier_settings": {
                        "enabled": bool(outlier_enabled),
                        "level": str(outlier_level),
                        "q_low": outlier_result.q_low,
                        "q_high": outlier_result.q_high,
                    },
                    "outlier_stats": {
                        "excluded_n": outlier_result.excluded_n,
                        "analysis_n_after_outlier": int(len(analysis_df)),
                    },
                }
            )

    return {"analyses": analyses}
