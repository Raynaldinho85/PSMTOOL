from __future__ import annotations

import pandas as pd

from psm_tool.core.metrics import compute_psm_kpis
from psm_tool.plots.psm_plot import make_psm_figure


def _sample_curves() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "price": [10.0, 20.0, 30.0, 40.0],
            "too_cheap": [90.0, 70.0, 30.0, 10.0],
            "bargain": [95.0, 80.0, 45.0, 20.0],
            "expensive": [5.0, 20.0, 55.0, 80.0],
            "too_expensive": [0.0, 15.0, 50.0, 85.0],
            "not_bargain": [5.0, 20.0, 55.0, 80.0],
            "not_expensive": [95.0, 80.0, 45.0, 20.0],
        }
    )


def test_psm_vertical_marker_labels_split_left_and_right() -> None:
    curves = _sample_curves()
    kpis = compute_psm_kpis(curves)
    fig = make_psm_figure(curves, kpis)

    anchors = {
        str(annotation.text): str(annotation.xanchor) for annotation in fig.layout.annotations
    }
    assert anchors["PMI"] == "right"
    assert anchors["OPP"] == "right"
    assert anchors["IDP"] == "left"
    assert anchors["PME"] == "left"


def test_psm_legend_title_is_hidden() -> None:
    fig = make_psm_figure(_sample_curves(), compute_psm_kpis(_sample_curves()))
    if fig.layout.legend and fig.layout.legend.title:
        legend_title = fig.layout.legend.title.text
    else:
        legend_title = None
    assert legend_title in (None, "")
