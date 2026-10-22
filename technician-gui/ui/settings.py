"""
Adjustable warning thresholds and PostgreSQL database connection management.
Exclusively standardized on Imperial units (°F) with Voltesse cyber styling.
"""

import streamlit as st

from data.db import get_db_url, test_connection


def show_settings():
    st.markdown(
        """
        <div style="margin-bottom: 12px;">
            <h2 style="margin: 0; padding: 0; font-weight: 800; letter-spacing: 0.05em; color: #FFFFFF;">
                ⚙️ SYSTEM & TELEMETRY SETTINGS
            </h2>
            <p style="margin: 0; padding: 0; font-size: 0.82rem; color: #94A3B8;">
                Configure telemetry alert limits, database connectivity, and technician calibration parameters.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("PostgreSQL Persistence Engine")
    is_connected, msg = test_connection()
    c1, c2 = st.columns([3, 1])
    c1.text_input("Database URL (VOLTESSE_DB_URL)", value=get_db_url(), disabled=True)
    if c2.button("Test Connection", width="stretch"):
        st.rerun()

    if is_connected:
        st.markdown(
            f"""
            <div style="background: rgba(0, 245, 212, 0.08); border: 1px solid rgba(0, 245, 212, 0.4); 
                        border-radius: 6px; padding: 8px 14px; margin-bottom: 14px;">
                <span class="v-pill v-pill-active">🟢 POSTGRESQL 16 CONNECTED</span>
                <span style="margin-left: 10px; font-size: 0.85rem; color: #E2E8F0;">{msg}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background: rgba(255, 184, 0, 0.08); border: 1px solid rgba(255, 184, 0, 0.4); 
                        border-radius: 6px; padding: 8px 14px; margin-bottom: 14px;">
                <span class="v-pill v-pill-standby">🟡 DATABASE STANDBY</span>
                <span style="margin-left: 10px; font-size: 0.85rem; color: #E2E8F0;">{msg}</span>
                <div style="margin-top: 6px; font-size: 0.78rem; color: #94A3B8;">
                    Launch local PostgreSQL container via Docker: <code>cd db && docker compose up -d</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("Telemetry Warning Thresholds (Imperial)")
    st.caption("Configure vehicle alert limits. These settings drive live warnings, notifications, and diagnostic chart thresholds.")

    st.session_state.warning_temp = st.slider(
        "Motor Temperature Warning Limit (°F)",
        min_value=110, max_value=230,
        value=st.session_state.get("warning_temp", 160), step=5,
        help="Nominal < 160°F | Warm >= 160°F | Hot >= 195°F",
    )
    st.session_state.warning_battery = st.slider(
        "Low Battery SoC Warning Limit (%)",
        min_value=5, max_value=40,
        value=st.session_state.get("warning_battery", 20), step=5,
        help="Triggers low energy alert when state-of-charge drops below this percentage.",
    )

    st.subheader("Active Calibration Summary")
    left, right = st.columns(2)
    left.metric(
        "Motor Temp Warning Limit",
        f"{st.session_state.warning_temp} °F",
        delta="Imperial Standard",
        delta_color="off",
        border=True,
    )
    right.metric(
        "Low Battery SoC Limit",
        f"{st.session_state.warning_battery}%",
        delta="Pack Threshold",
        delta_color="off",
        border=True,
    )
