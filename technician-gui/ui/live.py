"""Live telemetry view (four MVP cards and temperature history)."""

import plotly.graph_objects as go
import streamlit as st

from data.simulator import live_metrics, live_temperature_history


def show_live():
    st.title("Live Telemetry")
    st.caption("Voltesse Dash | Simulated Vehicle Data")

    simulation_time = st.slider(
        "Simulation Time (seconds)", min_value=0, max_value=120, value=30, step=5,
    )
    values = live_metrics(simulation_time)

    st.subheader("Vehicle Status")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Speed", f"{values['speed']} MPH", border=True)
    col2.metric("Motor RPM", f"{values['rpm']:,}", border=True)
    col3.metric("Battery", f"{values['battery']}%", border=True)
    col4.metric("Motor Temperature", f"{values['temperature']} °C", border=True)

    st.divider()

    # One shared setting drives both the visible warning and red graph limit.
    high_temp = values["temperature"] >= st.session_state.warning_temp
    low_battery = values["battery"] <= st.session_state.warning_battery
    if high_temp:
        st.error("WARNING: High Motor Temperature!")
    if low_battery:
        st.warning("WARNING: Low Battery!")
    if not high_temp and not low_battery:
        st.success("Vehicle Status: Normal")

    st.subheader("Motor Temperature (Last 60 Seconds)")
    times, temperatures = live_temperature_history(simulation_time)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=temperatures, mode="lines", name="Motor Temperature",
        line=dict(color="#E39A2D", width=3),
    ))
    fig.add_hline(
        y=st.session_state.warning_temp, line_dash="dash", line_color="red",
        annotation_text="Warning Limit", annotation_position="top right",
    )
    fig.update_layout(
        xaxis_title="Simulation Time (seconds)",
        yaxis_title="Temperature (°C)", height=400,
        margin=dict(l=30, r=30, t=40, b=30),
    )
    st.plotly_chart(fig, width="stretch")
