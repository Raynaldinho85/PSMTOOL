from __future__ import annotations

from importlib import resources
from io import BytesIO

import pandas as pd
import streamlit as st

from psm_tool.config import AppConfig
from psm_tool.io.read_any import SAVDependencyError, read_any
from psm_tool.io.validate import template_columns, validate_template


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


def _store_dataset(df: pd.DataFrame) -> None:
    result = validate_template(df)
    st.session_state["psm_validation_errors"] = result.errors
    st.session_state["psm_validation_warnings"] = result.warnings
    st.session_state["psm_analysis_payload"] = None

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


def main() -> None:
    config = AppConfig()
    st.title("1. Upload")
    st.caption("Accepted formats: CSV, XLSX, SAV")
    st.info("Files are processed in-memory only and never persisted by default.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "Download CSV template",
            data=_csv_template_bytes(),
            file_name="psm_template.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            "Download XLSX template",
            data=_xlsx_template_bytes(),
            file_name="psm_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col3:
        if st.button("Load example dataset"):
            _store_dataset(_load_sample_dataset())
            st.success("Loaded synthetic packaged example dataset.")

    uploaded = st.file_uploader("Upload input dataset", type=["csv", "xlsx", "sav"])
    if uploaded is not None:
        try:
            frame = read_any(uploaded.getvalue(), filename=uploaded.name)
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
                _store_dataset(frame)
                st.success(f"Loaded '{uploaded.name}' with {len(frame)} rows.")

    _render_validation_messages()

    current_df = st.session_state.get("psm_input_df")
    if current_df is None:
        st.info("No valid dataset loaded yet.")
        return

    st.success("Dataset is valid for analysis.")
    st.write(f"Rows: **{len(current_df)}** | Columns: **{len(current_df.columns)}**")
    if config.demo_mode:
        st.caption("DEMO_MODE hides raw row preview.")
    else:
        st.dataframe(current_df.head(30), use_container_width=True)


if __name__ == "__main__":
    main()
