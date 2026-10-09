"""Voltesse Dash — Technician/Admin Streamlit presentation prototype.

Run from the project root: python -m streamlit run app.py
Uses simulated telemetry only; login is NOT real authentication.
"""

import streamlit as st

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

    # These are custom pages, NOT Streamlit's automatic pages/ directory.
    st.sidebar.title("VOLTESSE DASH")
    st.sidebar.caption("Technician / Admin")
    st.sidebar.divider()

    page = st.sidebar.radio(
        "Navigation",
        ["Live", "Diagnostics", "Sessions", "Settings"],
    )
    st.sidebar.divider()

    if st.sidebar.button("Sign Out"):
        st.session_state.logged_in = False
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
