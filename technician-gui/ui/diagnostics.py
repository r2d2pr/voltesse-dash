"""Five session-specific performance charts arranged 3 + 2, querying PostgreSQL with fallback."""

import plotly.graph_objects as go
import streamlit as st

from data.db import get_diagnostics_data


def compact_chart(figure):
    """Make five charts compact enough for a presentation display."""
    figure.update_layout(
        height=210, showlegend=False,
        margin=dict(l=45, r=10, t=10, b=35), font=dict(size=10),
        template="plotly_dark",
    )
    figure.update_xaxes(title_font=dict(size=10), tickfont=dict(size=9), nticks=4)
    figure.update_yaxes(title_font=dict(size=10), tickfont=dict(size=9), nticks=4)
    return figure


def show_diagnostics():
    st.header("Vehicle Diagnostics")

    selected = st.session_state.get("selected_session")
    data, is_db = get_diagnostics_data(selected)

    if is_db:
        st.caption("Voltesse Dash | 🟢 Connected to PostgreSQL — Real Session Telemetry Analysis")
    else:
        st.caption("Voltesse Dash | 🟡 Simulated Performance Analysis (PostgreSQL Offline or Sample Session)")

    if selected:
        st.info(
            f"Viewing Session {selected['id']} | Date: {selected['date']} | "
            f"Duration: {selected['duration']} | Max Temperature: {selected['max_temp']} °C"
        )
    else:
        st.info("No session selected. Showing benchmark telemetry. Visit Sessions to pick a specific run.")

    top_cols = st.columns(3, gap="small")
    bottom_cols = st.columns(2, gap="small")

    # Graph 1: Efficiency vs. Speed
    top_cols[0].markdown("**Energy Efficiency vs. Speed**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["speeds"], y=data["efficiency"], mode="lines+markers",
        name="Energy Efficiency", line=dict(color="#00F5A0", width=3),
        marker=dict(size=5),
    ))
    fig.update_layout(
        xaxis_title="Vehicle Speed (MPH)",
        yaxis_title="Energy Consumption (Wh/mi)",
    )
    top_cols[0].plotly_chart(compact_chart(fig), width="stretch")

    # Graph 2: Power vs. Motor Temperature
    top_cols[1].markdown("**Power Draw vs. Motor Temperature**")
    fig_power = go.Figure()
    fig_power.add_trace(go.Scatter(
        x=data["motor_temps"], y=data["power_draws"],
        mode="markers", name="Measurements",
        marker=dict(color="#00E5FF", size=7),
    ))
    fig_power.add_trace(go.Scatter(
        x=data["motor_temps"], y=data["trend_power"],
        mode="lines", name="Trend", line=dict(color="#5CFFC7", width=2),
    ))
    fig_power.update_layout(
        xaxis_title="Motor Temperature (°C)",
        yaxis_title="Power Draw (W)",
    )
    top_cols[1].plotly_chart(compact_chart(fig_power), width="stretch")

    # Graph 3: Battery vs. Distance
    top_cols[2].markdown("**Battery Consumption vs. Distance**")
    fig_battery = go.Figure()
    fig_battery.add_trace(go.Scatter(
        x=data["distances"], y=data["battery_levels"],
        mode="lines+markers", name="Battery Remaining",
        line=dict(color="#2E8B57", width=3), marker=dict(size=4),
    ))
    fig_battery.update_layout(
        xaxis_title="Distance Traveled (miles)",
        yaxis_title="Battery Remaining (%)", yaxis=dict(range=[0, 100]),
    )
    top_cols[2].plotly_chart(compact_chart(fig_battery), width="stretch")

    # Graph 4: Power vs. RPM
    bottom_cols[0].markdown("**Power Draw vs. Motor RPM**")
    fig_rpm = go.Figure()
    fig_rpm.add_trace(go.Scatter(
        x=data["motor_rpms"], y=data["power_values"],
        mode="markers", name="Measurements",
        marker=dict(color="#FFB703", size=7),
    ))
    fig_rpm.add_trace(go.Scatter(
        x=data["motor_rpms"], y=data["trend_values"],
        mode="lines", name="Power Trend", line=dict(color="#FB8500", width=3),
    ))
    fig_rpm.update_layout(
        xaxis_title="Motor Speed (RPM)",
        yaxis_title="Power Draw (W)",
    )
    bottom_cols[0].plotly_chart(compact_chart(fig_rpm), width="stretch")

    # Graph 5: Temperature rise vs. Time, with the Settings threshold
    bottom_cols[1].markdown("**Motor Temperature Rise Over Time**")
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(
        x=data["time_minutes"], y=data["temp_rise"],
        mode="lines", name="Motor Temperature",
        line=dict(color="#FF4D6D", width=3),
    ))
    fig_temp.add_hline(
        y=st.session_state.warning_temp, line_dash="dash", line_color="red",
        annotation_text="Warning Limit", annotation_position="top right",
    )
    fig_temp.update_layout(
        xaxis_title="Operation Time (minutes)",
        yaxis_title="Motor Temperature (°C)",
        yaxis=dict(range=[20, max(65, data["peak_temp"] + 10, st.session_state.warning_temp + 10)]),
    )
    bottom_cols[1].plotly_chart(compact_chart(fig_temp), width="stretch")
