from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from psm_tool.io.validate import normalize_pi_pair_units


@dataclass(slots=True)
class NMSResult:
    curves: pd.DataFrame
    max_trial_price: float
    max_revenue_price: float
    base_n: int
    included_n: int
    puki_filter_applied: bool
    puki_threshold: int | None
    weighting_applied: bool
    filter_note: str | None = None
    pi_unit_note: str | None = None


def _interp_segment(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    if np.isclose(x1, x0):
        return y1
    ratio = (x - x0) / (x1 - x0)
    return y0 + ratio * (y1 - y0)


def _respondent_trial(row: pd.Series, prices: np.ndarray) -> np.ndarray:
    tc = float(row["too_cheap"])
    bargain = float(row["bargain"])
    acceptable = float(row["expensive_acceptable"])
    te = float(row["too_expensive"])
    pi_bargain = float(np.clip(row["pi_bargain_pct"], 0.0, 100.0))
    pi_expensive = float(np.clip(row["pi_expensive_pct"], 0.0, 100.0))

    out = np.zeros_like(prices, dtype=float)
    for idx, price in enumerate(prices):
        if price <= tc or price >= te:
            out[idx] = 0.0
        elif price <= bargain:
            out[idx] = _interp_segment(price, tc, 0.0, bargain, pi_bargain)
        elif price <= acceptable:
            out[idx] = _interp_segment(price, bargain, pi_bargain, acceptable, pi_expensive)
        else:
            out[idx] = _interp_segment(price, acceptable, pi_expensive, te, 0.0)
    return out


def _select_population(
    df_group: pd.DataFrame, puki_threshold: int
) -> tuple[pd.DataFrame, bool, str | None]:
    if "puki" not in df_group.columns:
        return df_group.copy(), False, "PUKI filter not applied because 'puki' column is missing."

    puki_numeric = pd.to_numeric(df_group["puki"], errors="coerce")
    include_mask = puki_numeric <= float(puki_threshold)
    selected = df_group.loc[include_mask.fillna(False)].copy()
    return selected, True, None


def resolve_nms_weights(df: pd.DataFrame, weight_col: str | None) -> tuple[np.ndarray, bool]:
    if weight_col and weight_col in df.columns:
        weights = pd.to_numeric(df[weight_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        weights[weights < 0] = 0.0
        if np.sum(weights) > 0:
            return weights, True
        return np.ones(len(df), dtype=float), False
    return np.ones(len(df), dtype=float), False


def _empty_nms_result(
    prices: np.ndarray,
    base_n: int,
    included_n: int,
    puki_filter_applied: bool,
    puki_threshold: int | None,
    weighting_applied: bool,
    note: str | None,
    pi_unit_note: str | None,
) -> NMSResult:
    curves = pd.DataFrame(
        {
            "price": prices,
            "trial_pct": np.nan,
            "revenue_per_100": np.nan,
            "turnover_index": np.nan,
        }
    )
    return NMSResult(
        curves=curves,
        max_trial_price=float("nan"),
        max_revenue_price=float("nan"),
        base_n=base_n,
        included_n=included_n,
        puki_filter_applied=puki_filter_applied,
        puki_threshold=puki_threshold,
        weighting_applied=weighting_applied,
        filter_note=note,
        pi_unit_note=pi_unit_note,
    )


def compute_nms(
    df_group: pd.DataFrame,
    prices: np.ndarray,
    *,
    weight_col: str | None = None,
    puki_threshold: int = 2,
) -> NMSResult:
    required = [
        "too_cheap",
        "bargain",
        "expensive_acceptable",
        "too_expensive",
        "pi_bargain_pct",
        "pi_expensive_pct",
    ]
    missing = [col for col in required if col not in df_group.columns]
    if missing:
        raise ValueError(
            f"NMS requires columns: {', '.join(required)}. Missing: {', '.join(missing)}"
        )

    prices = np.asarray(prices, dtype=float)
    base_n = int(len(df_group))
    selected, filter_applied, note = _select_population(df_group, puki_threshold=puki_threshold)
    try:
        selected, pi_unit_note = normalize_pi_pair_units(selected)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    selected = selected.dropna(subset=required).copy()
    included_n = int(len(selected))
    threshold_out = puki_threshold if filter_applied else None

    if included_n == 0:
        return _empty_nms_result(
            prices=prices,
            base_n=base_n,
            included_n=0,
            puki_filter_applied=filter_applied,
            puki_threshold=threshold_out,
            weighting_applied=False,
            note=note,
            pi_unit_note=pi_unit_note,
        )

    respondent_curves = np.vstack(
        [_respondent_trial(row, prices) for _, row in selected.iterrows()]
    )
    weights, weighting_applied = resolve_nms_weights(selected, weight_col=weight_col)
    trial_pct = np.average(respondent_curves, axis=0, weights=weights)

    revenue = (trial_pct / 100.0) * prices * 100.0
    max_revenue = float(np.max(revenue))
    if max_revenue <= 0:
        turnover = np.zeros_like(revenue)
    else:
        turnover = revenue / max_revenue * 100.0

    max_trial_price = float(prices[int(np.nanargmax(trial_pct))])
    max_revenue_price = float(prices[int(np.nanargmax(revenue))])

    curves = pd.DataFrame(
        {
            "price": prices,
            "trial_pct": trial_pct,
            "revenue_per_100": revenue,
            "turnover_index": turnover,
        }
    )

    return NMSResult(
        curves=curves,
        max_trial_price=max_trial_price,
        max_revenue_price=max_revenue_price,
        base_n=base_n,
        included_n=included_n,
        puki_filter_applied=filter_applied,
        puki_threshold=threshold_out,
        weighting_applied=weighting_applied,
        filter_note=note,
        pi_unit_note=pi_unit_note,
    )
