"""Core computational logic for PSM Tool."""

from psm_tool.core.curves import compute_psm_curves
from psm_tool.core.grid import build_price_grid, build_price_grid_details
from psm_tool.core.metrics import PSMKPIResult, compute_psm_kpis
from psm_tool.core.nms import NMSResult, compute_nms
from psm_tool.core.outliers import OutlierFilterResult, apply_outlier_filter
from psm_tool.core.qc import QCResult, apply_psm_validity_filter, compute_qc_report
from psm_tool.core.turnover_index import (
    TurnoverIndexResult,
    align_pi_ladder_to_grid,
    compute_turnover_index,
    resolve_purchase_intention_curve,
)

__all__ = [
    "NMSResult",
    "OutlierFilterResult",
    "PSMKPIResult",
    "QCResult",
    "TurnoverIndexResult",
    "apply_outlier_filter",
    "apply_psm_validity_filter",
    "align_pi_ladder_to_grid",
    "build_price_grid",
    "build_price_grid_details",
    "compute_nms",
    "compute_psm_curves",
    "compute_psm_kpis",
    "compute_qc_report",
    "compute_turnover_index",
    "resolve_purchase_intention_curve",
]
