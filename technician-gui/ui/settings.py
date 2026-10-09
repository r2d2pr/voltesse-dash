"""Adjustable local warning thresholds for the presentation prototype."""

import streamlit as st


def show_settings():
    st.title("Dashboard Settings")
    st.caption("Voltesse Dash | Technician / Admin")
    st.subheader("Warning Thresholds")
    st.write("Configure the warning limits used to monitor vehicle operating conditions.")

    # Keep persistent values separate from Streamlit's temporary slider widget
    # identity, so navigating between pages will not reset the thresholds.
    st.session_state.warning_temp = st.slider(
        "Motor Temperature Warning (°C)",
        min_value=40, max_value=110,
        value=st.session_state.warning_temp, step=5,
    )
    st.session_state.warning_battery = st.slider(
        "Low Battery Warning (%)", min_value=5, max_value=40,
        value=st.session_state.warning_battery, step=5,
    )

    st.divider()
    st.subheader("Current Warning Configuration")
    left, right = st.columns(2)
    left.metric("Temperature Warning", f"{st.session_state.warning_temp} °C", border=True)
    right.metric("Low Battery Warning", f"{st.session_state.warning_battery}%", border=True)
    st.info("Demo settings only. Values are stored temporarily for this browser session.")
