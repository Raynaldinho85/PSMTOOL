from __future__ import annotations

import importlib.util
from pathlib import Path

from psm_tool.core.additional_metrics import MetricResult


def _load_results_module():
    page_path = Path("src/psm_tool/ui/pages/2_results.py")
    spec = importlib.util.spec_from_file_location("module_results_helpers", page_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_format_intersection_value_handles_clean_interval_closest() -> None:
    module = _load_results_module()
    kpis = {
        "pmi": 12.5,
        "pmi_status": "clean",
        "opp": 20.0,
        "opp_status": "interval",
        "opp_low": 19.0,
        "opp_high": 21.0,
        "idp": 30.0,
        "idp_status": "closest",
    }

    clean_value, clean_caution = module._format_intersection_value(
        kpis, key="pmi", price_symbol="EUR "
    )
    assert clean_value == "EUR 12.50"
    assert clean_caution is None

    interval_value, interval_caution = module._format_intersection_value(
        kpis, key="opp", price_symbol="EUR "
    )
    assert interval_value == "[EUR 19.00, EUR 21.00] (~ EUR 20.00)"
    assert interval_caution == "interval"

    closest_value, closest_caution = module._format_intersection_value(
        kpis, key="idp", price_symbol="EUR "
    )
    assert closest_value == "EUR 30.00 (diagnostic)"
    assert closest_caution == "closest"


def test_format_additional_metric_value_suppresses_unstable_values() -> None:
    module = _load_results_module()
    unstable_metric = MetricResult(
        key="revenue_efficiency",
        label="Revenue Efficiency",
        lens="Cross-layer: Perception vs Economics proxy",
        is_stable=False,
        value=None,
        diagnostic_value=1.23,
        reason="Requires clean OPP.",
    )

    stable_metric = MetricResult(
        key="profit_feasibility_zone",
        label="Profit Feasibility Zone",
        lens="Cross-layer: Perception vs Economics proxy",
        is_stable=True,
        value=62.4,
        diagnostic_value=62.4,
        reason=None,
    )

    unstable_value, unstable_caution = module._format_additional_metric_value(
        unstable_metric,
        price_symbol="EUR ",
    )
    assert unstable_value == "—"
    assert unstable_caution == "unstable"

    stable_value, stable_caution = module._format_additional_metric_value(
        stable_metric,
        price_symbol="EUR ",
    )
    assert stable_value == "62.4%"
    assert stable_caution is None


def test_results_tab_specs_insert_kpi_summary_before_quality_control() -> None:
    module = _load_results_module()

    with_nms = module._build_results_tab_specs(
        has_turnover=True,
        has_profit=True,
        has_nms=True,
    )
    without_nms = module._build_results_tab_specs(
        has_turnover=True,
        has_profit=False,
        has_nms=False,
    )

    assert with_nms[-3:] == [
        ("NMS Trial + Revenue", "nms_trial_revenue"),
        ("KPI Summary", "kpi_summary"),
        ("Quality Control", "quality_control"),
    ]
    assert without_nms[-2:] == [
        ("KPI Summary", "kpi_summary"),
        ("Quality Control", "quality_control"),
    ]
