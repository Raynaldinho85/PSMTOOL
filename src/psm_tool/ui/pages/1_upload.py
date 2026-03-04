from __future__ import annotations

from importlib import resources
from io import BytesIO

import pandas as pd
import streamlit as st

from psm_tool.io.validate import template_columns


def _template_columns() -> list[str]:
    return template_columns()


def _empty_template_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_template_columns())


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


def main() -> None:
    st.title("1. Upload")
    st.write("Accepted types: CSV, XLSX, SAV (SAV support is optional via `psm-tool[sav]`).")

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
            st.session_state["psm_input_df"] = _load_sample_dataset()
            st.success("Loaded packaged synthetic example dataset.")

    uploaded = st.file_uploader("Upload input file", type=["csv", "xlsx", "sav"])
    if uploaded is not None:
        st.session_state["psm_uploaded_file"] = uploaded
        st.info("File received. Parsing and validation is enabled in Milestone 3.")


if __name__ == "__main__":
    main()
