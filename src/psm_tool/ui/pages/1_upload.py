from __future__ import annotations

from importlib import resources
from io import BytesIO

import pandas as pd
import streamlit as st

from psm_tool.config import AppConfig
from psm_tool.i18n import get_language, tr
from psm_tool.io.read_any import (
    SAVDependencyError,
    SAVUploadNotSupportedError,
    read_any,
    read_optional_pi_ladder,
)
from psm_tool.io.validate import template_columns, validate_template
from psm_tool.ui.auth import require_auth
from psm_tool.ui.page_nav import render_page_nav_bottom, render_page_nav_top
from psm_tool.ui.style import inject_base_styles, render_notice
from psm_tool.ui.upload_state import clear_loaded_dataset_state, has_loaded_dataset


def _empty_template_df() -> pd.DataFrame:
    return pd.DataFrame(columns=template_columns())


def _csv_template_bytes() -> bytes:
    return _empty_template_df().to_csv(index=False).encode("utf-8")


def _xlsx_template_bytes() -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _empty_template_df().to_excel(writer, sheet_name="template", index=False)
    return output.getvalue()


def _load_sample_dataset() -> pd.DataFrame:
    with (
        resources.files("psm_tool.resources").joinpath("sample_psm.csv").open("rb") as sample_handle
    ):
        return pd.read_csv(sample_handle)


def _store_dataset(
    df: pd.DataFrame,
    *,
    source_name: str,
    pi_ladder_df: pd.DataFrame | None = None,
) -> None:
    result = validate_template(df)
    st.session_state["psm_validation_errors"] = result.errors
    st.session_state["psm_validation_warnings"] = result.warnings
    st.session_state["psm_analysis_payload"] = None
    st.session_state["psm_pi_ladder_df"] = pi_ladder_df
    st.session_state["psm_input_source"] = source_name

    if result.is_valid:
        st.session_state["psm_input_df"] = result.normalized_df
    else:
        st.session_state["psm_input_df"] = None


def _display_source_name(source_name: str) -> str:
    if source_name.strip().lower() == "sample_psm.csv":
        return tr("demo_psm.csv (synthetic example dataset)")
    return source_name


def _render_validation_messages() -> None:
    errors = st.session_state.get("psm_validation_errors", [])
    warnings = st.session_state.get("psm_validation_warnings", [])

    for error in errors:
        render_notice(str(error))
    for warning in warnings:
        render_notice(str(warning))


def _render_loaded_dataset_summary(df: pd.DataFrame, *, demo_mode: bool) -> None:
    language = get_language()
    segments = int(df["segment"].nunique(dropna=True)) if "segment" in df.columns else 0
    products = int(df["product_id"].nunique(dropna=True)) if "product_id" in df.columns else 0
    currencies = int(df["currency"].nunique(dropna=True)) if "currency" in df.columns else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(tr("Rows", language), f"{len(df)}")
    col2.metric(tr("Columns", language), f"{len(df.columns)}")
    col3.metric(tr("Countries", language), f"{segments}")
    col4.metric(tr("Product Categories", language), f"{products}")
    col5.metric(tr("Currencies", language), f"{currencies}")

    if demo_mode:
        st.caption(tr("DEMO_MODE hides raw row preview.", language))
        return

    with st.expander(tr("Preview first 30 rows", language), expanded=False):
        st.dataframe(df.head(30), width="stretch")


def main() -> None:
    require_auth()
    config = AppConfig()
    inject_base_styles(max_width=2800)
    language = get_language()

    st.markdown(
        f'<p class="psm-page-eyebrow">{tr("Data Intake", language)}</p>',
        unsafe_allow_html=True,
    )
    st.title(tr("1. Upload", language))
    st.caption(tr("Accepted formats: CSV, XLSX", language))
    render_page_nav_top("upload")

    with st.container(border=True):
        st.markdown(
            tr(
                (
                    "Privacy safeguard: all uploaded files are processed "
                    "in-memory and not persisted by default."
                ),
                language,
            )
        )

    with st.container(border=True):
        st.markdown(
            f'<div class="psm-card-title">{tr("Template and Demo Data", language)}</div>',
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                tr("Download CSV template", language),
                data=_csv_template_bytes(),
                file_name="psm_template.csv",
                mime="text/csv",
                width="stretch",
            )
        with col2:
            st.download_button(
                tr("Download XLSX template", language),
                data=_xlsx_template_bytes(),
                file_name="psm_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        with col3:
            if st.button(tr("Load example dataset", language), width="stretch"):
                _store_dataset(
                    _load_sample_dataset(),
                    source_name="sample_psm.csv",
                    pi_ladder_df=None,
                )

    with st.container(border=True):
        st.markdown(
            f'<div class="psm-card-title">{tr("Upload Input File", language)}</div>',
            unsafe_allow_html=True,
        )
        if has_loaded_dataset(st.session_state):
            source = str(st.session_state.get("psm_input_source") or "loaded dataset")
            source = _display_source_name(source)
            render_notice(
                tr("Current dataset loaded: {source}", language, source=source),
                tone="positive",
            )
            if st.button(
                tr("Remove current dataset", language),
                type="secondary",
                width="stretch",
            ):
                clear_loaded_dataset_state(st.session_state)
                st.rerun()
        else:
            uploaded = st.file_uploader(
                tr("Choose input dataset", language),
                type=["csv", "xlsx"],
                help=tr("Required template columns must match exactly.", language),
            )
            if uploaded is not None:
                try:
                    payload = uploaded.getvalue()
                    frame = read_any(payload, filename=uploaded.name)
                except SAVDependencyError as exc:
                    render_notice(str(exc))
                except SAVUploadNotSupportedError as exc:
                    render_notice(str(exc))
                except Exception as exc:
                    render_notice(f"Failed to read '{uploaded.name}': {exc}")
                else:
                    if config.demo_mode and len(frame) > config.max_rows_demo:
                        render_notice(
                            tr(
                                (
                                    "DEMO_MODE upload limit exceeded: {rows} "
                                    "rows provided, max {limit} allowed."
                                ),
                                language,
                                rows=len(frame),
                                limit=config.max_rows_demo,
                            )
                        )
                    else:
                        auto_ladder = read_optional_pi_ladder(payload, filename=uploaded.name)
                        _store_dataset(
                            frame,
                            source_name=uploaded.name,
                            pi_ladder_df=auto_ladder,
                        )
                        render_notice(
                            tr(
                                "Loaded '{filename}' with {rows} rows.",
                                language,
                                filename=uploaded.name,
                                rows=len(frame),
                            ),
                            tone="positive",
                        )
                        if auto_ladder is not None:
                            render_notice(
                                tr(
                                    (
                                        "Detected optional purchase intention "
                                        "ladder table (sheet "
                                        "'purchase_intention')."
                                    ),
                                    language,
                                ),
                                tone="positive",
                            )

    _render_validation_messages()

    current_df = st.session_state.get("psm_input_df")
    if current_df is None:
        render_notice(tr("No valid dataset loaded yet.", language))
        render_page_nav_bottom("upload")
        return

    with st.container(border=True):
        render_notice(tr("Dataset loaded and valid for analysis.", language), tone="positive")
        _render_loaded_dataset_summary(current_df, demo_mode=config.demo_mode)

    render_page_nav_bottom("upload")


if __name__ == "__main__":
    main()
