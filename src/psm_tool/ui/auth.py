from __future__ import annotations

import streamlit as st

from psm_tool.config import AppConfig
from psm_tool.i18n import get_language, tr

AUTH_SESSION_KEY = "psm_authorized"
AUTH_INPUT_KEY = "_psm_auth_password_input"


def require_auth() -> None:
    expected_password = AppConfig().app_password
    if not expected_password:
        st.session_state[AUTH_SESSION_KEY] = True
        return

    if st.session_state.get(AUTH_SESSION_KEY, False):
        return

    language = get_language()
    provided = st.text_input(
        tr("Application password", language),
        type="password",
        key=AUTH_INPUT_KEY,
    )
    if provided == expected_password:
        st.session_state[AUTH_SESSION_KEY] = True
        st.session_state.pop(AUTH_INPUT_KEY, None)
        st.rerun()

    st.caption(
        tr(
            "Authentication required. Enter the application password to continue.",
            language,
        )
    )
    st.stop()
