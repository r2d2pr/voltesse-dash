"""Live telemetry view (four MVP cards and temperature history)."""

import plotly.graph_objects as go
import streamlit as st

from data import source


def show_live():
    st.title("Live Telemetry")
    if source.USING_DB:
        st.caption("Voltesse Dash | Latest reading from the database (refreshes every second)")
        live_from_db()
        return

    st.caption("Voltesse Dash | Simulated Vehicle Data")
    simulation_time = st.slider(
        "Simulation Time (seconds)", min_value=0, max_value=120, value=30, step=5,
    )
    times, temperatures = source.live_temperature_history(simulation_time)
    show_vehicle_status(source.live_metrics(simulation_time), times, temperatures,
                        "Simulation Time (seconds)")


@st.fragment(run_every=1)
def live_from_db():
    values = source.latest_metrics()
    if values is None:
        st.info("No telemetry recorded yet. Start the dashboard (main.py) to log a session.")
        return
    times, temperatures = source.temperature_history()
    show_vehicle_status(values, times, temperatures, "Time Into Session (seconds)")


def show_vehicle_status(values, times, temperatures, x_title):
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
        xaxis_title=x_title,
        yaxis_title="Temperature (°C)", height=400,
        margin=dict(l=30, r=30, t=40, b=30),
    )
    st.plotly_chart(fig, width="stretch")
