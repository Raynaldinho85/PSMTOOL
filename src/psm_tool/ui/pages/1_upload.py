from __future__ import annotations

from importlib import resources
from io import BytesIO

import pandas as pd
import streamlit as st

from psm_tool.config import AppConfig
from psm_tool.io.read_any import (
    SAVDependencyError,
    read_any,
    read_optional_pi_ladder,
    read_pi_ladder,
)
from psm_tool.io.validate import template_columns, validate_template
from psm_tool.ui.style import inject_base_styles


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


def _store_dataset(df: pd.DataFrame, *, pi_ladder_df: pd.DataFrame | None = None) -> None:
    result = validate_template(df)
    st.session_state["psm_validation_errors"] = result.errors
    st.session_state["psm_validation_warnings"] = result.warnings
    st.session_state["psm_analysis_payload"] = None
    st.session_state["psm_pi_ladder_df"] = pi_ladder_df

    if result.is_valid:
        st.session_state["psm_input_df"] = result.normalized_df
    else:
        st.session_state["psm_input_df"] = None


def _render_validation_messages() -> None:
    errors = st.session_state.get("psm_validation_errors", [])
    warnings = st.session_state.get("psm_validation_warnings", [])

    for error in errors:
        st.error(error)
    for warning in warnings:
        st.warning(warning)


def _render_loaded_dataset_summary(df: pd.DataFrame, *, demo_mode: bool) -> None:
    segments = int(df["segment"].nunique(dropna=True)) if "segment" in df.columns else 0
    products = int(df["product_id"].nunique(dropna=True)) if "product_id" in df.columns else 1
    currencies = int(df["currency"].nunique(dropna=True)) if "currency" in df.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{len(df)}")
    col2.metric("Columns", f"{len(df.columns)}")
    col3.metric("Segments", f"{segments}")
    col4.metric("Products / Currencies", f"{products} / {currencies}")

    if demo_mode:
        st.caption("DEMO_MODE hides raw row preview.")
        return

    with st.expander("Preview first 30 rows", expanded=False):
        st.dataframe(df.head(30), use_container_width=True)


def main() -> None:
    config = AppConfig()
    inject_base_styles(max_width=1400)

    st.title("1. Upload")
    st.caption("Accepted formats: CSV, XLSX, SAV")

    with st.container(border=True):
        st.markdown(
            "Privacy safeguard: all uploaded files are processed in-memory "
            "and not persisted by default."
        )

    with st.container(border=True):
        st.subheader("Template and Demo Data")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "Download CSV template",
                data=_csv_template_bytes(),
                file_name="psm_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                "Download XLSX template",
                data=_xlsx_template_bytes(),
                file_name="psm_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col3:
            if st.button("Load example dataset", use_container_width=True):
                _store_dataset(_load_sample_dataset(), pi_ladder_df=None)
                st.success("Loaded synthetic packaged example dataset.")

    with st.container(border=True):
        st.subheader("Upload Input File")
        uploaded = st.file_uploader(
            "Choose input dataset",
            type=["csv", "xlsx", "sav"],
            help="Required template columns must match exactly.",
        )
        if uploaded is not None:
            try:
                payload = uploaded.getvalue()
                frame = read_any(payload, filename=uploaded.name)
            except SAVDependencyError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Failed to read '{uploaded.name}': {exc}")
            else:
                if config.demo_mode and len(frame) > config.max_rows_demo:
                    st.error(
                        "DEMO_MODE upload limit exceeded: "
                        f"{len(frame)} rows provided, max {config.max_rows_demo} allowed."
                    )
                else:
                    auto_ladder = read_optional_pi_ladder(payload, filename=uploaded.name)
                    _store_dataset(frame, pi_ladder_df=auto_ladder)
                    st.success(f"Loaded '{uploaded.name}' with {len(frame)} rows.")
                    if auto_ladder is not None:
                        st.info(
                            "Detected optional purchase intention ladder table "
                            "(sheet 'purchase_intention')."
                        )

        pi_upload = st.file_uploader(
            "Optional PI ladder file (CSV/XLSX)",
            type=["csv", "xlsx"],
            key="pi_ladder_upload",
            help="Accepted: *_pi.csv or XLSX sheet named 'purchase_intention'.",
        )
        if pi_upload is not None:
            try:
                ladder = read_pi_ladder(pi_upload.getvalue(), filename=pi_upload.name)
            except Exception as exc:
                st.error(f"Failed to read PI ladder '{pi_upload.name}': {exc}")
            else:
                st.session_state["psm_pi_ladder_df"] = ladder
                st.success(f"Loaded PI ladder '{pi_upload.name}' with {len(ladder)} rows.")

    _render_validation_messages()

    current_df = st.session_state.get("psm_input_df")
    if current_df is None:
        st.info("No valid dataset loaded yet.")
        return

    with st.container(border=True):
        st.success("Dataset is valid for analysis.")
        _render_loaded_dataset_summary(current_df, demo_mode=config.demo_mode)


if __name__ == "__main__":
    main()
