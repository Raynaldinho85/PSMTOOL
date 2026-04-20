from __future__ import annotations

import importlib.util
from pathlib import Path

import plotly.graph_objects as go

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


def test_results_tab_specs_localize_nms_tab_for_german() -> None:
    module = _load_results_module()

    with_nms = module._build_results_tab_specs(
        has_turnover=False,
        has_profit=False,
        has_nms=True,
        language="de",
    )

    assert ("NMS Kaufabsicht + Umsatz", "nms_trial_revenue") in with_nms


def test_results_tab_specs_localize_profit_tab_for_german() -> None:
    module = _load_results_module()

    with_profit = module._build_results_tab_specs(
        has_turnover=False,
        has_profit=True,
        has_nms=False,
        language="de",
    )

    assert ("Profit-Index (0-100)", "profit") in with_profit


def test_results_page_uses_explicit_apply_forms_for_enter_sensitive_controls() -> None:
    source = Path("src/psm_tool/ui/pages/2_results.py").read_text(encoding="utf-8")

    assert source.count("enter_to_submit=False") >= 3
    assert source.count('st.form_submit_button(tr("Apply", language))') >= 3
    assert 'tr("Changes take effect after clicking Apply.", language)' in source


def test_results_page_only_shows_details_for_active_tested_price_and_economics_states() -> None:
    source = Path("src/psm_tool/ui/pages/2_results.py").read_text(encoding="utf-8")

    assert "economics_details_visible = economics_draft_enabled or stored_economics_enabled" in source
    assert "if economics_details_visible:" in source
    assert "tested_price_details_visible = (" in source
    assert "tested_price_draft_value is not None" in source
    assert "or stored_tested_price is not None" in source
    assert "or stored_tested_price_active" in source


def test_results_page_does_not_write_back_into_draft_widget_keys_after_submit() -> None:
    source = Path("src/psm_tool/ui/pages/2_results.py").read_text(encoding="utf-8")

    economics_section = source.split(
        'economics_submitted = st.form_submit_button(tr("Apply", language))',
        1,
    )[1].split('tested_price_map: dict[str, float]', 1)[0]
    tested_price_section = source.split(
        'tested_price_submitted = st.form_submit_button(tr("Apply", language))',
        1,
    )[1].split("opp_for_manual_default =", 1)[0]
    manual_grid_section = source.split(
        'manual_grid_submitted = st.form_submit_button(tr("Apply", language))',
        1,
    )[1].split("unit_cost = float(cost_map.get(unit_cost_key, 0.0))", 1)[0]

    assert "st.session_state[economics_toggle_key] = economics_enabled" not in economics_section
    assert "st.session_state[unit_cost_input_key] = stored_unit_cost" not in economics_section
    assert "st.session_state[tested_price_input_key]" not in tested_price_section
    assert "st.session_state[tested_price_active_key]" not in tested_price_section
    assert "st.session_state[manual_min_draft_key] = manual_min" not in manual_grid_section
    assert "st.session_state[manual_max_draft_key] = manual_max" not in manual_grid_section
    assert "st.session_state[manual_step_draft_key] = manual_step" not in manual_grid_section


def test_apply_psm_axis_footer_localizes_valid_and_total_for_german() -> None:
    module = _load_results_module()
    figure = go.Figure()

    module._apply_psm_axis_footer(
        figure,
        selected_product="Classic",
        selected_segment="DE",
        currency="EUR",
        total_n=120,
        valid_n=90,
        analysis_n=80,
        language="de",
    )

    annotation_text = [str(annotation.text) for annotation in figure.layout.annotations]
    assert any("gültig: 90 / gesamt: 120" in text for text in annotation_text)


def test_marker_override_widget_sync_roundtrip_updates_chart_overrides() -> None:
    module = _load_results_module()
    module.st.session_state.clear()
    selection_key = "Classic::DE"
    marker_options_by_chart = {
        "psm": [("pmi", "PMI")],
        "turnover": [("max_turnover_price", "Maximum Turnover")],
        "nms": [("max_trial", "MaxTrial"), ("max_revenue", "MaxRevenue")],
    }

    module.st.session_state[module._marker_override_widget_key(selection_key, "psm", "pmi")] = (
        "Left"
    )
    module.st.session_state[
        module._marker_override_widget_key(
            selection_key,
            "turnover",
            "max_turnover_price",
        )
    ] = "Right"
    module.st.session_state[
        module._marker_override_widget_key(selection_key, "nms", "max_trial")
    ] = "Right"

    module._sync_marker_overrides_from_widgets(
        selection_key=selection_key,
        marker_options_by_chart=marker_options_by_chart,
    )

    assert module._marker_label_side_overrides(selection_key, "psm") == {"pmi": "left"}
    assert module._marker_label_side_overrides(selection_key, "turnover") == {
        "max_turnover_price": "right"
    }
    assert module._marker_label_side_overrides(selection_key, "nms") == {"max_trial": "right"}
