from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pandas as pd
from streamlit.testing.v1 import AppTest

from psm_tool.ui import page_nav


RESULTS_PAGE = Path("src/psm_tool/ui/pages/2_results.py")


def _results_input_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_id": ["Classic"] * 4,
            "segment": ["DE"] * 4,
            "currency": ["EUR"] * 4,
            "too_cheap": [12.0, 14.0, 16.0, 15.0],
            "bargain": [22.0, 24.0, 26.0, 25.0],
            "expensive_acceptable": [34.0, 36.0, 38.0, 37.0],
            "too_expensive": [48.0, 50.0, 52.0, 51.0],
        }
    )


def _make_results_app_test(monkeypatch) -> AppTest:
    temp_root = Path(".apptest_tmp") / uuid4().hex
    temp_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMP", str(temp_root))
    monkeypatch.setenv("TEMP", str(temp_root))
    monkeypatch.setenv("TMPDIR", str(temp_root))
    monkeypatch.setattr(tempfile, "tempdir", str(temp_root), raising=False)
    monkeypatch.setattr(page_nav, "render_page_nav_top", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(page_nav, "render_page_nav_bottom", lambda *_args, **_kwargs: None)

    app = AppTest.from_file(str(RESULTS_PAGE), default_timeout=5)
    app.session_state["psm_authorized"] = True
    app.session_state["app_language"] = "en"
    app.session_state["psm_input_df"] = _results_input_df()
    app.session_state["psm_validation_errors"] = []
    app.session_state["psm_validation_warnings"] = []
    app.session_state["psm_pi_ladder_df"] = None
    return app


def _toggle_by_label(app: AppTest, label: str):
    return next(toggle for toggle in app.toggle if toggle.label == label)


def _selectbox_by_label(app: AppTest, label: str):
    return next(selectbox for selectbox in app.selectbox if selectbox.label == label)


def _text_input_by_label(app: AppTest, label: str):
    return next(text_input for text_input in app.text_input if text_input.label == label)


def _button_by_label(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_results_detail_controls_only_appear_for_active_states(monkeypatch) -> None:
    app = _make_results_app_test(monkeypatch)

    app.run()

    assert not any(widget.label == "Unit cost" for widget in app.number_input)
    assert not any(widget.label == "Show Tested Price" for widget in app.toggle)

    _toggle_by_label(app, "Economics").set_value(True)
    app.run()

    assert any(widget.label == "Unit cost" for widget in app.number_input)

    _text_input_by_label(app, "Tested Price").set_value("25")
    app.run()

    assert any(widget.label == "Show Tested Price" for widget in app.toggle)


def test_marker_override_survives_tested_price_apply_and_stays_editable(monkeypatch) -> None:
    app = _make_results_app_test(monkeypatch)
    selection_key = "Classic::DE"

    app.run()

    _selectbox_by_label(app, "PMI").set_value("Left")
    app.run()

    assert app.session_state["marker_label_side_overrides_by_key"][selection_key]["psm"] == {
        "pmi": "left"
    }

    _text_input_by_label(app, "Tested Price").set_value("25")
    app.run()
    _button_by_label(app, "Apply").click()
    app.run()

    pmi_selectbox = _selectbox_by_label(app, "PMI")
    assert pmi_selectbox.value == "Left"
    assert app.session_state["marker_label_side_overrides_by_key"][selection_key]["psm"] == {
        "pmi": "left"
    }

    pmi_selectbox.set_value("Right")
    app.run()

    assert _selectbox_by_label(app, "PMI").value == "Right"
    assert app.session_state["marker_label_side_overrides_by_key"][selection_key]["psm"] == {
        "pmi": "right"
    }
