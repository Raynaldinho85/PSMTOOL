from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pptx import Presentation


def build_pptx_report(template_path: str | Path | None = None) -> bytes:
    presentation = (
        Presentation(template_path)
        if template_path and Path(template_path).exists()
        else Presentation()
    )
    title_layout = presentation.slide_layouts[0]
    slide = presentation.slides.add_slide(title_layout)
    slide.shapes.title.text = "PSM Tool Report"
    subtitle = slide.placeholders[1]
    subtitle.text = "Generated from in-memory analysis."

    output = BytesIO()
    presentation.save(output)
    return output.getvalue()
