"""
Technician & Race Engineer login with PostgreSQL authentication and presentation demo fallback.
Mercedes-AMG F1 Pit-Wall visual theme.
"""

import streamlit as st

from data.db import authenticate_user, test_connection


def show_login():
    st.markdown(
        """
        <div style="text-align: center; margin-top: 30px; margin-bottom: 24px;">
            <div style="font-size: 2.5rem; font-weight: 900; letter-spacing: 0.15em; color: #00F5D4;">
                ⚡ VOLTESSE
            </div>
            <div style="font-size: 0.9rem; font-weight: 700; letter-spacing: 0.2em; color: #E2E8F0; margin-top: 4px;">
                MERCEDES-AMG F1 TELEMETRY PIT-WALL
            </div>
            <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 4px;">
                Technician & Race Engineer Command Portal (v5.0.0)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    is_connected, msg = test_connection()

    _, center, _ = st.columns([1, 1.4, 1])
    with center:
        if is_connected:
            st.markdown(
                f"""
                <div style="background: rgba(0, 245, 212, 0.08); border: 1px solid rgba(0, 245, 212, 0.35); 
                            border-radius: 6px; padding: 6px 12px; margin-bottom: 16px; text-align: center;">
                    <span class="f1-pill f1-pill-active">🟢 POSTGRESQL LINKED</span>
                    <span style="font-size: 0.8rem; color: #E2E8F0; margin-left: 6px;">{msg}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background: rgba(255, 184, 0, 0.08); border: 1px solid rgba(255, 184, 0, 0.35); 
                            border-radius: 6px; padding: 6px 12px; margin-bottom: 16px; text-align: center;">
                    <span class="f1-pill f1-pill-standby">🟡 DEMO BENCH MODE</span>
                    <span style="font-size: 0.8rem; color: #E2E8F0; margin-left: 6px;">
                        PostgreSQL Standby (Demo authentication available)
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.form("login_form"):
            st.markdown("<div style='font-weight: 700; color: #00F5D4; font-size: 0.9rem;'>AUTHENTICATION</div>", unsafe_allow_html=True)
            username = st.text_input("Username or Email", value="tech_demo")
            password = st.text_input("Password", type="password", value="Demo123!")
            login = st.form_submit_button("Access Pit-Wall Telemetry", width="stretch")

        st.caption("Demo Account: `tech_demo` &nbsp;|&nbsp; Password: `Demo123!`")

        if login:
            success, user = authenticate_user(username, password)
            if success and user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Authentication failed. Please verify credentials.")
