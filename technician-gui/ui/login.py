"""Simulated technician login; no actual authentication/security."""

import streamlit as st


def show_login():
    st.title("VOLTESSE DASH")
    st.caption("Technician / Admin Sign In")

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.subheader("Technician Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login = st.form_submit_button("Sign In", width="stretch")

        st.caption("Demo account: demo@voltesse.test")
        st.caption("Demo password: Demo123!")
        st.caption("Presentation-only login. Do not enter real credentials.")

        if login:
            if email == "demo@voltesse.test" and password == "Demo123!":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Incorrect demo credentials.")
