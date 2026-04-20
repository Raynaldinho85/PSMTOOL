"""Core computational logic for PSM Tool."""

from psm_tool.core.curves import compute_psm_curves
from psm_tool.core.grid import build_price_grid, build_price_grid_details
from psm_tool.core.metrics import PSMKPIResult, compute_psm_kpis
from psm_tool.core.nms import NMSResult, compute_nms
from psm_tool.core.outliers import OutlierFilterResult, apply_outlier_filter
from psm_tool.core.qc import (
    QCResult,
    apply_psm_validity_filter,
    apply_puki_filter,
    compute_qc_report,
    puki_eligibility_mask,
)
from psm_tool.core.turnover_index import (
    ProfitProxyResult,
    TurnoverIndexResult,
    align_pi_ladder_to_grid,
    compute_profit_proxy,
    compute_turnover_index,
    resolve_purchase_intention_curve,
)

__all__ = [
    "NMSResult",
    "OutlierFilterResult",
    "PSMKPIResult",
    "QCResult",
    "ProfitProxyResult",
    "TurnoverIndexResult",
    "apply_outlier_filter",
    "apply_psm_validity_filter",
    "apply_puki_filter",
    "align_pi_ladder_to_grid",
    "build_price_grid",
    "build_price_grid_details",
    "compute_profit_proxy",
    "compute_nms",
    "compute_psm_curves",
    "compute_psm_kpis",
    "compute_qc_report",
    "compute_turnover_index",
    "puki_eligibility_mask",
    "resolve_purchase_intention_curve",
]
