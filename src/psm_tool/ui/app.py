from __future__ import annotations

import streamlit as st

from psm_tool.config import AppConfig


def _check_password(config: AppConfig) -> None:
    if not config.app_password:
        return

    provided = st.text_input("Application password", type="password")
    if provided != config.app_password:
        st.warning("Enter a valid password to continue.")
        st.stop()


def main() -> None:
    config = AppConfig()
    st.set_page_config(page_title="PSM Tool", page_icon=":bar_chart:", layout="wide")
    st.title("PSM Tool")
    st.caption("Van Westendorp PSM + optional NMS extension")
    st.info("Privacy: uploaded files are processed in-memory and not stored on disk.")

    _check_password(config)
    st.write("Use the sidebar pages to upload data, inspect results, and export reports.")

    if config.demo_mode:
        st.warning(
            "DEMO_MODE is enabled: stricter upload limits and reduced data visibility are active."
        )


if __name__ == "__main__":
    main()
