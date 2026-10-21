"""Adjustable warning thresholds and PostgreSQL database connection management."""

import streamlit as st

from data.db import get_db_url, test_connection


def show_settings():
    st.title("Admin & System Settings")
    st.caption("Voltesse Dash | Technician / Admin Configuration")

    st.subheader("PostgreSQL Database Integration")
    is_connected, msg = test_connection()
    c1, c2 = st.columns([3, 1])
    c1.text_input("Database URL (VOLTESSE_DB_URL)", value=get_db_url(), disabled=True)
    if c2.button("Test Connection", width="stretch"):
        st.rerun()

    if is_connected:
        st.success(f"🟢 Database Status: {msg}")
    else:
        st.warning(f"🟡 Database Status: {msg}")
        st.caption("Start PostgreSQL locally via Docker: `cd db && docker compose up -d` or set `$env:VOLTESSE_DB_URL`.")

    st.divider()

    st.subheader("Telemetry Warning Thresholds")
    st.write("Configure vehicle alert limits. These settings drive live warnings and diagnostic chart thresholds.")

    st.session_state.warning_temp = st.slider(
        "Motor Temperature Warning (°C)",
        min_value=40, max_value=110,
        value=st.session_state.warning_temp, step=5,
    )
    st.session_state.warning_battery = st.slider(
        "Low Battery Warning (%)", min_value=5, max_value=40,
        value=st.session_state.warning_battery, step=5,
    )

    st.subheader("Active Configuration Summary")
    left, right = st.columns(2)
    left.metric("Temperature Warning Limit", f"{st.session_state.warning_temp} °C", border=True)
    right.metric("Low Battery Warning Limit", f"{st.session_state.warning_battery}%", border=True)
