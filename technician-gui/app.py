"""Voltesse Dash — Technician/Admin Streamlit Web Interface v3.0.

Communicates with the PostgreSQL database backend to deliver live vehicle telemetry,
session logs, diagnostics performance charts, and alert threshold settings.
Run with: streamlit run app.py
"""

import streamlit as st

from data.db import test_connection
from ui.diagnostics import show_diagnostics
from ui.live import show_live
from ui.login import show_login
from ui.sessions import show_sessions
from ui.settings import show_settings

st.set_page_config(
    page_title="Voltesse Dash | Technician",
    page_icon="🏎️",
    layout="wide",
)


def initialize_state():
    """Create shared defaults once per Streamlit browser session."""
    defaults = {
        "logged_in": False,
        "warning_temp": 60,
        "warning_battery": 20,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main():
    initialize_state()

    if not st.session_state.logged_in:
        show_login()
        return

    user = st.session_state.get("user", {"name": "Technician", "role": "TECHNICIAN"})
    st.sidebar.title("VOLTESSE DASH")
    st.sidebar.caption(f"Technician / Admin • {user.get('name', 'User')}")
    st.sidebar.badge(user.get("role", "TECHNICIAN"))
    st.sidebar.divider()

    page = st.sidebar.radio(
        "Navigation",
        ["Live", "Diagnostics", "Sessions", "Settings"],
    )
    st.sidebar.divider()

    if st.sidebar.button("Sign Out", width="stretch"):
        st.session_state.logged_in = False
        st.session_state.pop("user", None)
        st.rerun()

    pages = {
        "Live": show_live,
        "Diagnostics": show_diagnostics,
        "Sessions": show_sessions,
        "Settings": show_settings,
    }
    pages[page]()


if __name__ == "__main__":
    main()
