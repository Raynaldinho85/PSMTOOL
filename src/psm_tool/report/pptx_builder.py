from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt

from psm_tool.plots.nms_plot import make_nms_figure
from psm_tool.plots.psm_plot import make_psm_figure
from psm_tool.plots.render_static import figure_to_png_bytes
from psm_tool.plots.turnover_index_plot import make_pi_economics_figure, make_turnover_index_figure
from psm_tool.report.insights import (
    build_nms_summary,
    build_profit_summary,
    build_psm_summary,
    build_turnover_summary,
)

EMU_PER_INCH = 914400.0


def _new_presentation(template_path: str | Path | None = None) -> Presentation:
    if template_path and Path(template_path).exists():
        return Presentation(str(template_path))
    return Presentation()


def _emu_to_in(value: int) -> float:
    return float(value) / EMU_PER_INCH


def _slide_size_in(presentation: Presentation) -> tuple[float, float]:
    return _emu_to_in(int(presentation.slide_width)), _emu_to_in(int(presentation.slide_height))


def _add_title(slide, *, x: float, y: float, width: float, text: str) -> float:
    title_h = 0.52
    title_box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(title_h))
    frame = title_box.text_frame
    frame.text = text
    frame.paragraphs[0].font.size = Pt(26)
    frame.paragraphs[0].font.bold = True
    return title_h


def _add_context_line(
    slide,
    *,
    x: float,
    y: float,
    width: float,
    analysis: dict[str, Any],
) -> float:
    context_h = 0.30
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(context_h))
    frame = box.text_frame
    frame.text = f"{analysis['product_id']} / {analysis['segment']} ({analysis['currency']})"
    frame.paragraphs[0].font.size = Pt(12)
    return context_h


def _add_bullet_text(
    slide,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    sentences: list[str],
    max_items: int,
    font_size: int,
) -> None:
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
    frame = box.text_frame
    frame.clear()
    for idx, sentence in enumerate(sentences[:max_items]):
        paragraph = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
        paragraph.text = f"- {sentence}"
        paragraph.font.size = Pt(font_size)


def _headline_from_sentence(sentence: str, fallback: str) -> str:
    text = sentence.strip()
    if not text:
        return fallback
    if len(text) <= 96:
        return text
    short = text[:93].rstrip(" ,;:.")
    return f"{short}..."


def _psm_action_title(analysis: dict[str, Any]) -> str:
    kpis = analysis["kpis"]
    sentence = (
        "Set price in accepted range "
        f"{kpis['accepted_low']:.2f}-{kpis['accepted_high']:.2f} {analysis['currency']}."
    )
    return _headline_from_sentence(sentence, "Set price within the accepted range.")


def _turnover_action_title(analysis: dict[str, Any]) -> str:
    turnover = analysis.get("turnover_index_result")
    if turnover is None:
        return "Maximize turnover at the modeled optimum."
    sentence = f"Maximize turnover near {turnover.max_turnover_price:.2f} {analysis['currency']}."
    return _headline_from_sentence(sentence, "Maximize turnover at the modeled optimum.")


def _nms_action_title(analysis: dict[str, Any]) -> str:
    nms_result = analysis.get("nms_result")
    if nms_result is None:
        return "Align trial and revenue peaks in NMS."
    sentence = (
        f"Balance trial ({nms_result.max_trial_price:.2f}) and revenue "
        f"({nms_result.max_revenue_price:.2f}) in {analysis['currency']}."
    )
    return _headline_from_sentence(sentence, "Balance trial and revenue peaks.")


def _profit_action_title(analysis: dict[str, Any]) -> str:
    profit = analysis.get("profit_proxy_result")
    if profit is None:
        return "Optimize price for profit proxy."
    sentence = f"Optimize profit proxy near {profit.max_profit_price:.2f} {analysis['currency']}."
    return _headline_from_sentence(sentence, "Optimize price for profit proxy.")


def _add_kpi_summary(
    slide,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    analysis: dict[str, Any],
) -> None:
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

    text_box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
    frame = text_box.text_frame
    frame.clear()
    for idx, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.size = Pt(13)


def _add_psm_slide(presentation: Presentation, analysis: dict[str, Any]) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide_w, slide_h = _slide_size_in(presentation)
    margin = 0.42
    content_w = slide_w - (2 * margin)
    gap = 0.14

    title_h = _add_title(
        slide,
        x=margin,
        y=0.16,
        width=content_w,
        text=_psm_action_title(analysis),
    )
    context_y = 0.16 + title_h + 0.05
    context_h = _add_context_line(
        slide,
        x=margin,
        y=context_y,
        width=content_w,
        analysis=analysis,
    )

    summary_h = min(1.45, max(1.10, slide_h * 0.18))
    summary_y = slide_h - margin - summary_h
    chart_top = context_y + context_h + 0.07
    chart_h = max(2.6, summary_y - chart_top - 0.08)

    kpi_w = min(3.7, max(2.8, content_w * 0.29))
    chart_w = max(4.6, content_w - kpi_w - gap)
    if (chart_w + kpi_w + gap) > content_w:
        kpi_w = max(2.4, content_w - chart_w - gap)
    chart_x = margin
    kpi_x = chart_x + chart_w + gap

    figure = make_psm_figure(analysis["curves"], analysis["kpi_result"])
    image_bytes = figure_to_png_bytes(figure)
    slide.shapes.add_picture(
        BytesIO(image_bytes),
        Inches(chart_x),
        Inches(chart_top),
        width=Inches(chart_w),
        height=Inches(chart_h),
    )

    _add_kpi_summary(
        slide,
        x=kpi_x,
        y=chart_top,
        width=max(2.2, content_w - chart_w - gap),
        height=chart_h,
        analysis=analysis,
    )
    _add_psm_summary_bullets(
        slide,
        analysis=analysis,
        x=margin,
        y=summary_y,
        width=content_w,
        height=summary_h,
    )


def _add_psm_summary_bullets(
    slide,
    *,
    analysis: dict[str, Any],
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
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
        product_label=str(analysis["product_id"]),
        nms_kpis=nms_kpis,
    )
    _add_bullet_text(
        slide,
        x=x,
        y=y,
        width=width,
        height=height,
        sentences=sentences,
        max_items=4,
        font_size=12,
    )


def _add_turnover_index_slide(presentation: Presentation, analysis: dict[str, Any]) -> bool:
    turnover_result = analysis.get("turnover_index_result")
    if turnover_result is None:
        return False

    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide_w, slide_h = _slide_size_in(presentation)
    margin = 0.42
    content_w = slide_w - (2 * margin)

    title_h = _add_title(
        slide,
        x=margin,
        y=0.16,
        width=content_w,
        text=_turnover_action_title(analysis),
    )
    context_y = 0.16 + title_h + 0.05
    context_h = _add_context_line(
        slide,
        x=margin,
        y=context_y,
        width=content_w,
        analysis=analysis,
    )

    summary_h = min(1.35, max(1.00, slide_h * 0.17))
    summary_y = slide_h - margin - summary_h
    chart_top = context_y + context_h + 0.07
    chart_h = max(2.55, summary_y - chart_top - 0.08)

    figure = make_turnover_index_figure(turnover_result, currency=analysis["currency"])
    image_bytes = figure_to_png_bytes(figure)
    slide.shapes.add_picture(
        BytesIO(image_bytes),
        Inches(margin),
        Inches(chart_top),
        width=Inches(content_w),
        height=Inches(chart_h),
    )

    summary_sentences = build_turnover_summary(
        turnover_result,
        currency=analysis["currency"],
        segment_label=str(analysis["segment"]),
        source=analysis.get("turnover_source"),
    )
    _add_bullet_text(
        slide,
        x=margin,
        y=summary_y,
        width=content_w,
        height=summary_h,
        sentences=summary_sentences,
        max_items=3,
        font_size=12,
    )
    return True


def _add_nms_slide(presentation: Presentation, analysis: dict[str, Any]) -> None:
    nms_result = analysis.get("nms_result")
    if nms_result is None:
        return

    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide_w, slide_h = _slide_size_in(presentation)
    margin = 0.42
    content_w = slide_w - (2 * margin)
    gap = 0.14

    title_h = _add_title(
        slide,
        x=margin,
        y=0.16,
        width=content_w,
        text=_nms_action_title(analysis),
    )
    context_y = 0.16 + title_h + 0.05
    context_h = _add_context_line(
        slide,
        x=margin,
        y=context_y,
        width=content_w,
        analysis=analysis,
    )

    summary_h = min(1.35, max(1.05, slide_h * 0.17))
    summary_y = slide_h - margin - summary_h
    chart_top = context_y + context_h + 0.07
    chart_h = max(2.55, summary_y - chart_top - 0.08)

    meta_w = min(3.2, max(2.6, content_w * 0.27))
    chart_w = max(4.5, content_w - meta_w - gap)
    if (chart_w + meta_w + gap) > content_w:
        meta_w = max(2.2, content_w - chart_w - gap)

    figure = make_nms_figure(nms_result)
    image_bytes = figure_to_png_bytes(figure)
    slide.shapes.add_picture(
        BytesIO(image_bytes),
        Inches(margin),
        Inches(chart_top),
        width=Inches(chart_w),
        height=Inches(chart_h),
    )

    box_x = margin + chart_w + gap
    box = slide.shapes.add_textbox(
        Inches(box_x),
        Inches(chart_top),
        Inches(meta_w),
        Inches(chart_h),
    )
    frame = box.text_frame
    frame.clear()
    lines = [
        f"Max Trial: {analysis['currency']} {nms_result.max_trial_price:.2f}",
        f"Max Revenue: {analysis['currency']} {nms_result.max_revenue_price:.2f}",
        f"Included N: {int(nms_result.included_n)}",
    ]
    for idx, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if idx == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.size = Pt(13)

    _add_nms_summary_bullets(
        slide,
        analysis=analysis,
        nms_result=nms_result,
        x=margin,
        y=summary_y,
        width=content_w,
        height=summary_h,
    )


def _add_profit_slide(presentation: Presentation, analysis: dict[str, Any]) -> bool:
    turnover_result = analysis.get("turnover_index_result")
    profit_result = analysis.get("profit_proxy_result")
    unit_cost = analysis.get("unit_cost")
    if turnover_result is None or profit_result is None or unit_cost is None:
        return False

    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide_w, slide_h = _slide_size_in(presentation)
    margin = 0.42
    content_w = slide_w - (2 * margin)

    title_h = _add_title(
        slide,
        x=margin,
        y=0.16,
        width=content_w,
        text=_profit_action_title(analysis),
    )
    context_y = 0.16 + title_h + 0.05
    context_h = _add_context_line(
        slide,
        x=margin,
        y=context_y,
        width=content_w,
        analysis=analysis,
    )

    summary_h = min(1.35, max(1.05, slide_h * 0.17))
    summary_y = slide_h - margin - summary_h
    chart_top = context_y + context_h + 0.07
    chart_h = max(2.55, summary_y - chart_top - 0.08)

    figure = make_pi_economics_figure(
        turnover_result,
        currency=analysis["currency"],
        mode="profit",
        profit_result=profit_result,
        unit_cost=float(unit_cost),
    )
    image_bytes = figure_to_png_bytes(figure)
    slide.shapes.add_picture(
        BytesIO(image_bytes),
        Inches(margin),
        Inches(chart_top),
        width=Inches(content_w),
        height=Inches(chart_h),
    )

    summary = build_profit_summary(
        profit_result,
        currency=analysis["currency"],
        segment_label=str(analysis["segment"]),
        product_label=str(analysis["product_id"]),
    )
    _add_bullet_text(
        slide,
        x=margin,
        y=summary_y,
        width=content_w,
        height=summary_h,
        sentences=summary,
        max_items=3,
        font_size=12,
    )
    return True


def _add_nms_summary_bullets(
    slide,
    *,
    analysis: dict[str, Any],
    nms_result: Any,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    sentences = build_nms_summary(
        nms_result=nms_result,
        currency=analysis["currency"],
        segment_label=str(analysis["segment"]),
    )
    _add_bullet_text(
        slide,
        x=x,
        y=y,
        width=width,
        height=height,
        sentences=sentences,
        max_items=4,
        font_size=12,
    )


def build_pptx_report(
    report_payload: dict[str, Any],
    template_path: str | Path | None = None,
) -> bytes:
    presentation = _new_presentation(template_path=template_path)
    analyses = report_payload.get("analyses", [])

    for analysis in analyses:
        _add_psm_slide(presentation, analysis)
        _add_turnover_index_slide(presentation, analysis)
        _add_profit_slide(presentation, analysis)
        _add_nms_slide(presentation, analysis)

    output = BytesIO()
    presentation.save(output)
    return output.getvalue()
