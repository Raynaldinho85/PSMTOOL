from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt

from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.psm_plot import make_psm_figure
from psm_tool.plots.render_static import figure_to_png_bytes
from psm_tool.plots.turnover_index_plot import make_turnover_index_figure
from psm_tool.report.insights import build_nms_summary, build_psm_summary


def _new_presentation(template_path: str | Path | None = None) -> Presentation:
    if template_path and Path(template_path).exists():
        return Presentation(str(template_path))
    return Presentation()


def _add_title(slide, title_text: str) -> None:
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(12.2), Inches(0.6))
    title_frame = title_box.text_frame
    title_frame.text = title_text
    title_frame.paragraphs[0].font.size = Pt(24)
    title_frame.paragraphs[0].font.bold = True


def _add_kpi_summary(slide, analysis: dict[str, Any]) -> None:
    kpis = analysis["kpis"]
    currency = analysis["currency"]
    outlier_settings = analysis.get("outlier_settings", {})
    outlier_stats = analysis.get("outlier_stats", {})
    outlier_enabled = bool(outlier_settings.get("enabled", False))
    if outlier_enabled:
        level = str(outlier_settings.get("level", "medium")).capitalize()
        q_low = outlier_settings.get("q_low")
        q_high = outlier_settings.get("q_high")
        excluded = int(outlier_stats.get("excluded_n", 0))
        outlier_line = (
            "Outlier filter: "
            f"{level} ({q_low * 100:.1f}%-{q_high * 100:.1f}%), excluded n={excluded}"
            if q_low is not None and q_high is not None
            else f"Outlier filter: {level}, excluded n={excluded}"
        )
    else:
        outlier_line = "Outlier filter: Off"

    lines = [
        f"PMI: {currency} {kpis['pmi']:.2f}",
        f"OPP: {currency} {kpis['opp']:.2f}",
        f"IDP: {currency} {kpis['idp']:.2f}",
        f"PME: {currency} {kpis['pme']:.2f}",
        "Accepted range: "
        f"{currency} {kpis['accepted_low']:.2f} - {currency} {kpis['accepted_high']:.2f}",
        f"Price stress (OPP-IDP): {kpis['price_stress']:.2f} [{kpis['stress_flag']}]",
        outlier_line,
    ]
    text_box = slide.shapes.add_textbox(Inches(8.0), Inches(1.1), Inches(4.8), Inches(4.8))
    frame = text_box.text_frame
    frame.clear()
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.size = Pt(14)


def _add_psm_slide(presentation: Presentation, analysis: dict[str, Any]) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    title = f"PSM - {analysis['product_id']} / {analysis['segment']}"
    _add_title(slide, title)

    figure = make_psm_figure(analysis["curves"], analysis["kpi_result"])
    image_bytes = figure_to_png_bytes(figure)
    slide.shapes.add_picture(BytesIO(image_bytes), Inches(0.5), Inches(1.0), width=Inches(7.2))
    _add_kpi_summary(slide, analysis)
    _add_summary_bullets(slide, analysis)


def _add_summary_bullets(slide, analysis: dict[str, Any]) -> None:
    nms_result = analysis.get("nms_result")
    nms_kpis = None
    if nms_result is not None:
        nms_kpis = {
            "max_trial_price": nms_result.max_trial_price,
            "max_revenue_price": nms_result.max_revenue_price,
        }

    sentences = build_psm_summary(
        analysis["kpis"],
        currency=analysis["currency"],
        segment_label=str(analysis["segment"]),
        nms_kpis=nms_kpis,
    )
    summary_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.7), Inches(12.0), Inches(1.6))
    frame = summary_box.text_frame
    frame.clear()
    for idx, sentence in enumerate(sentences):
        paragraph = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
        paragraph.text = f"- {sentence}"
        paragraph.font.size = Pt(12)


def _add_turnover_index_slide(presentation: Presentation, analysis: dict[str, Any]) -> bool:
    turnover_result = analysis.get("turnover_index_result")
    if turnover_result is None:
        return False

    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    _add_title(slide, "Purchase Intention & Turnover Index")

    subtitle = slide.shapes.add_textbox(Inches(0.5), Inches(0.85), Inches(12.0), Inches(0.5))
    subtitle_frame = subtitle.text_frame
    subtitle_frame.text = (
        "The highest turnover can be achieved by setting the price at "
        f"{turnover_result.max_turnover_price:.2f} {analysis['currency']}."
    )
    subtitle_frame.paragraphs[0].font.size = Pt(16)

    figure = make_turnover_index_figure(turnover_result, currency=analysis["currency"])
    image_bytes = figure_to_png_bytes(figure)
    slide.shapes.add_picture(BytesIO(image_bytes), Inches(0.5), Inches(1.3), width=Inches(12.0))
    return True


def _add_nms_slide(presentation: Presentation, analysis: dict[str, Any]) -> None:
    nms_result = analysis.get("nms_result")
    if nms_result is None:
        return

    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    title = f"NMS - {analysis['product_id']} / {analysis['segment']}"
    _add_title(slide, title)

    figure = make_nms_figure(nms_result)
    image_bytes = figure_to_png_bytes(figure)
    slide.shapes.add_picture(BytesIO(image_bytes), Inches(0.5), Inches(1.0), width=Inches(8.0))

    box = slide.shapes.add_textbox(Inches(8.7), Inches(1.2), Inches(3.8), Inches(2.5))
    frame = box.text_frame
    frame.text = f"MaxTrial: {analysis['currency']} {nms_result.max_trial_price:.2f}"
    frame.paragraphs[0].font.size = Pt(14)
    paragraph = frame.add_paragraph()
    paragraph.text = f"MaxRevenue: {analysis['currency']} {nms_result.max_revenue_price:.2f}"
    paragraph.font.size = Pt(14)
    _add_nms_summary_bullets(slide, analysis, nms_result)


def _add_nms_summary_bullets(slide, analysis: dict[str, Any], nms_result) -> None:
    sentences = build_nms_summary(
        nms_result=nms_result,
        currency=analysis["currency"],
        segment_label=str(analysis["segment"]),
    )
    summary_box = slide.shapes.add_textbox(Inches(0.5), Inches(5.7), Inches(12.0), Inches(1.6))
    frame = summary_box.text_frame
    frame.clear()
    for idx, sentence in enumerate(sentences):
        paragraph = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
        paragraph.text = f"- {sentence}"
        paragraph.font.size = Pt(12)


def build_pptx_report(
    report_payload: dict[str, Any],
    template_path: str | Path | None = None,
) -> bytes:
    presentation = _new_presentation(template_path=template_path)
    analyses = report_payload.get("analyses", [])

    for analysis in analyses:
        _add_psm_slide(presentation, analysis)
        added_turnover_slide = _add_turnover_index_slide(presentation, analysis)
        if not added_turnover_slide:
            _add_nms_slide(presentation, analysis)

    output = BytesIO()
    presentation.save(output)
    return output.getvalue()
