"""Live telemetry view connecting to PostgreSQL database with fallback to simulation slider."""

import plotly.graph_objects as go
import streamlit as st

from data.db import get_live_metrics, get_live_temperature_history
from data.simulator import live_metrics as mock_live_metrics, live_temperature_history as mock_live_temp_history


def show_live():
    st.title("Live Telemetry")

    # Source selection
    data_source = st.radio(
        "Telemetry Feed Source",
        ["Live PostgreSQL Database", "Interactive Simulation Slider"],
        horizontal=True,
    )

    if data_source == "Live PostgreSQL Database":
        values, is_db = get_live_metrics()
        if is_db:
            st.caption(f"Voltesse Dash | 🟢 Connected to PostgreSQL — Source: {values.get('signal_status', 'ACTIVE')}")
            times, temperatures, _ = get_live_temperature_history(seconds=60)
            time_label = "Telemetry Readings Sequence"
        else:
            st.caption("Voltesse Dash | 🟡 PostgreSQL has no active telemetry records. Using baseline feed.")
            values = mock_live_metrics(30)
            times, temperatures = mock_live_temp_history(30)
            time_label = "Simulation Time (seconds)"
    else:
        st.caption("Voltesse Dash | 🎮 Interactive Simulation Mode")
        simulation_time = st.slider(
            "Simulation Time (seconds)", min_value=0, max_value=120, value=30, step=5,
        )
        values = mock_live_metrics(simulation_time)
        times, temperatures = mock_live_temp_history(simulation_time)
        time_label = "Simulation Time (seconds)"

    st.subheader("Vehicle Status")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Speed", f"{values['speed']} MPH", border=True)
    col2.metric("Motor RPM", f"{values['rpm']:,}", border=True)
    col3.metric("Battery SoC", f"{values['battery']}%", border=True)
    col4.metric("Motor Temperature", f"{values['temperature']} °C", border=True)

    # Extra electrical diagnostics if available
    if "voltage" in values and "current" in values:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Pack Voltage", f"{values['voltage']} V", border=True)
        e2.metric("Current Draw", f"{values['current']} A", border=True)
        e3.metric("Gear / Trans", f"{values.get('gear', 'D')} ({values.get('transmission_mode', 'AUTO')})", border=True)
        e4.metric("Drive Mode", f"{values.get('drive_mode', 'DRIVE')}", border=True)

    st.divider()

    # One shared setting drives both the visible warning and red graph limit.
    high_temp = values["temperature"] >= st.session_state.warning_temp
    low_battery = values["battery"] <= st.session_state.warning_battery
    if high_temp:
        st.error(f"⚠️ WARNING: High Motor Temperature ({values['temperature']} °C >= limit {st.session_state.warning_temp} °C)!")
    if low_battery:
        st.warning(f"⚠️ WARNING: Low Battery Level ({values['battery']}% <= limit {st.session_state.warning_battery}%)!")
    if not high_temp and not low_battery:
        st.success("Vehicle Status: Normal (All Telemetry Within Operational Limits)")

    st.subheader("Motor Temperature Trend (Recent Window)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=temperatures, mode="lines+markers", name="Motor Temperature",
        line=dict(color="#00F5A0", width=3), marker=dict(size=4),
    ))
    fig.add_hline(
        y=st.session_state.warning_temp, line_dash="dash", line_color="red",
        annotation_text="Warning Limit", annotation_position="top right",
    )
    fig.update_layout(
        xaxis_title=time_label,
        yaxis_title="Temperature (°C)", height=380,
        margin=dict(l=30, r=30, t=40, b=30),
        template="plotly_dark",
    )
    st.plotly_chart(fig, width="stretch")
