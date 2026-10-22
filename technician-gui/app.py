"""Voltesse Dash — Telemetry Command Center (v5.0.0).

Communicates directly with the PostgreSQL persistence engine to deliver real-time
vehicle telemetry, synchronized telemetry traces, session analysis, and diagnostic logs.
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
    page_title="Voltesse | Telemetry Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_voltesse_theme():
    """Inject Voltesse automotive cyber styling: deep obsidian void, emerald cyan accents, silver metallic badges."""
    custom_css = """
    <style>
    /* Voltesse Cyber-Mint & Obsidian Palette */
    :root {
        --v-cyan: #00F5D4;
        --v-emerald: #00A19B;
        --v-silver: #E2E8F0;
        --v-obsidian: #080C0E;
        --v-dark-card: #0D1418;
        --v-border: rgba(0, 245, 212, 0.22);
        --v-red: #FF4D6D;
        --v-amber: #FFB800;
        --font-mono: 'Consolas', 'SF Mono', 'Courier New', monospace;
    }

    /* Main background */
    .stApp {
        background-color: var(--v-obsidian);
        background-image: radial-gradient(circle at 50% 0%, rgba(0, 245, 212, 0.04) 0%, transparent 60%);
        color: var(--v-silver);
    }

    /* Top header bar */
    header[data-testid="stHeader"] {
        background-color: rgba(8, 12, 14, 0.85);
        backdrop-filter: blur(8px);
        border-bottom: 1px solid rgba(0, 245, 212, 0.15);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #070B0D;
        border-right: 1px solid rgba(0, 245, 212, 0.18);
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(0, 245, 212, 0.15);
    }

    /* Metric cards styling */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #0D1519, #090E11);
        border: 1px solid rgba(0, 245, 212, 0.20);
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: var(--v-cyan);
        transform: translateY(-2px);
    }
    div[data-testid="stMetric"] label {
        color: #94A3B8 !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-family: var(--font-mono) !important;
        font-weight: 700 !important;
    }

    /* Voltesse Command pill badges */
    .v-pill {
        display: inline-block;
        padding: 4px 10px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        border-radius: 4px;
        font-family: var(--font-mono);
    }
    .v-pill-active {
        background-color: rgba(0, 245, 212, 0.15);
        color: #00F5D4;
        border: 1px solid rgba(0, 245, 212, 0.4);
    }
    .v-pill-standby {
        background-color: rgba(255, 184, 0, 0.15);
        color: #FFB800;
        border: 1px solid rgba(255, 184, 0, 0.4);
    }
    .v-pill-alert {
        background-color: rgba(255, 77, 109, 0.15);
        color: #FF4D6D;
        border: 1px solid rgba(255, 77, 109, 0.4);
    }

    /* Plotly chart container styling */
    .stPlotlyChart {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(0, 245, 212, 0.12);
        background: #090E11;
    }

    /* Streamlit button styling */
    button[kind="primary"] {
        background-color: #00A19B !important;
        border-color: #00F5D4 !important;
        color: #080C0E !important;
        font-weight: 700 !important;
    }
    button[kind="primary"]:hover {
        background-color: #00F5D4 !important;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def initialize_state():
    """Create shared defaults in Imperial units (°F / MPH / mi)."""
    defaults = {
        "logged_in": False,
        "warning_temp": 160,  # Imperial Fahrenheit default (160°F limit)
        "warning_battery": 20,
        "live_stream_active": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main():
    initialize_state()
    inject_voltesse_theme()

    if not st.session_state.logged_in:
        show_login()
        return

    user = st.session_state.get("user", {"name": "Telemetry Engineer", "role": "LEAD TECHNICIAN"})
    
    st.sidebar.markdown(
        """
        <div style="padding: 4px 0 12px 0;">
            <div style="font-size: 1.25rem; font-weight: 900; letter-spacing: 0.12em; color: #00F5D4;">
                ⚡ VOLTESSE
            </div>
            <div style="font-size: 0.70rem; font-weight: 700; letter-spacing: 0.15em; color: #94A3B8;">
                TELEMETRY COMMAND CENTER
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.sidebar.caption(f"Telemetry Station • {user.get('name', 'Telemetry Engineer')}")
    st.sidebar.badge(user.get("role", "LEAD TECHNICIAN"))
    st.sidebar.divider()

    page = st.sidebar.radio(
        "TELEMETRY CHANNELS",
        ["Live Telemetry", "Diagnostics", "Sessions", "Settings"],
    )
    st.sidebar.divider()

    if st.sidebar.button("Sign Out", width="stretch"):
        st.session_state.logged_in = False
        st.session_state.pop("user", None)
        st.rerun()

    pages = {
        "Live Telemetry": show_live,
        "Diagnostics": show_diagnostics,
        "Sessions": show_sessions,
        "Settings": show_settings,
    }
    pages[page]()


if __name__ == "__main__":
    main()
