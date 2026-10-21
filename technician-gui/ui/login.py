"""Technician login with PostgreSQL authentication and presentation demo fallback."""

import streamlit as st

from data.db import authenticate_user, test_connection


def show_login():
    st.title("VOLTESSE DASH")
    st.caption("Technician / Admin Sign In")

    is_connected, msg = test_connection()
    if is_connected:
        st.success(f"🟢 Database Status: {msg}")
    else:
        st.info("🟡 Database Status: Offline (Running in Demo Fallback Mode)")

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.subheader("Technician Login")
        with st.form("login_form"):
            username = st.text_input("Username or Email", value="tech_demo")
            password = st.text_input("Password", type="password", value="Demo123!")
            login = st.form_submit_button("Sign In", width="stretch")

        st.caption("Demo / Seed account: `tech_demo` or `demo@voltesse.test`")
        st.caption("Default password: `Demo123!`")

        if login:
            success, user = authenticate_user(username, password)
            if success and user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Authentication failed. Please verify credentials.")
