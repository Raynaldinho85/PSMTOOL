from __future__ import annotations

import tempfile
from importlib import resources
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from psm_tool.config import AppConfig
from psm_tool.io.read_any import (
    SAVDependencyError,
    read_any,
    read_optional_pi_ladder,
)
from psm_tool.io.validate import template_columns, validate_template
from psm_tool.ui.style import inject_base_styles
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


def _sav_template_bytes() -> tuple[bytes | None, str | None]:
    try:
        import pyreadstat  # type: ignore[import-not-found]
    except ImportError:
        return (
            None,
            "SAV template download requires optional dependency 'pyreadstat' "
            "(install with: pip install -e .[sav]).",
        )

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".sav",
            prefix=".tmp_psm_template_",
            dir=Path.cwd(),
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
        pyreadstat.write_sav(_empty_template_df(), str(temp_path))
        return temp_path.read_bytes(), None
    except Exception as exc:
        return None, f"SAV template generation unavailable: {exc}"
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


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


def _render_validation_messages() -> None:
    errors = st.session_state.get("psm_validation_errors", [])
    warnings = st.session_state.get("psm_validation_warnings", [])

    for error in errors:
        st.error(error)
    for warning in warnings:
        st.warning(warning)


def _render_loaded_dataset_summary(df: pd.DataFrame, *, demo_mode: bool) -> None:
    segments = int(df["segment"].nunique(dropna=True)) if "segment" in df.columns else 0
    products = int(df["product_id"].nunique(dropna=True)) if "product_id" in df.columns else 0
    currencies = int(df["currency"].nunique(dropna=True)) if "currency" in df.columns else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Rows", f"{len(df)}")
    col2.metric("Columns", f"{len(df.columns)}")
    col3.metric("Segments", f"{segments}")
    col4.metric("Product Categories", f"{products}")
    col5.metric("Currencies", f"{currencies}")

    if demo_mode:
        st.caption("DEMO_MODE hides raw row preview.")
        return

    with st.expander("Preview first 30 rows", expanded=False):
        st.dataframe(df.head(30), use_container_width=True)


def main() -> None:
    config = AppConfig()
    inject_base_styles(max_width=1400)

    st.markdown('<p class="psm-page-eyebrow">Data Intake</p>', unsafe_allow_html=True)
    st.title("1. Upload")
    st.caption("Accepted formats: CSV, XLSX, SAV")

    with st.container(border=True):
        st.markdown(
            "Privacy safeguard: all uploaded files are processed in-memory "
            "and not persisted by default."
        )

    with st.container(border=True):
        st.markdown(
            '<div class="psm-card-title">Template and Demo Data</div>',
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4 = st.columns(4)
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
            sav_bytes, sav_hint = _sav_template_bytes()
            st.download_button(
                "Download SAV template",
                data=sav_bytes if sav_bytes is not None else b"",
                file_name="psm_template.sav",
                mime="application/octet-stream",
                use_container_width=True,
                disabled=sav_bytes is None,
                help=sav_hint if sav_hint else "SPSS template with the required schema.",
            )
        with col4:
            if st.button("Load example dataset", use_container_width=True):
                _store_dataset(
                    _load_sample_dataset(),
                    source_name="sample_psm.csv",
                    pi_ladder_df=None,
                )
                st.success("Loaded synthetic packaged example dataset.")

    with st.container(border=True):
        st.markdown('<div class="psm-card-title">Upload Input File</div>', unsafe_allow_html=True)
        if has_loaded_dataset(st.session_state):
            source = str(st.session_state.get("psm_input_source") or "loaded dataset")
            st.markdown(
                (
                    "<p class='psm-upload-state'>Current dataset loaded: "
                    f"<strong>{source}</strong></p>"
                ),
                unsafe_allow_html=True,
            )
            if st.button("Remove current dataset", type="secondary", use_container_width=True):
                clear_loaded_dataset_state(st.session_state)
                st.rerun()
        else:
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
                        _store_dataset(
                            frame,
                            source_name=uploaded.name,
                            pi_ladder_df=auto_ladder,
                        )
                        st.success(f"Loaded '{uploaded.name}' with {len(frame)} rows.")
                        if auto_ladder is not None:
                            st.info(
                                "Detected optional purchase intention ladder table "
                                "(sheet 'purchase_intention')."
                            )

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
