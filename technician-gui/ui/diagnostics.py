"""Five session-specific performance charts arranged 3 + 2 for the MVP."""

import plotly.graph_objects as go
import streamlit as st

from data import source


def compact_chart(figure):
    """Make five charts compact enough for a presentation display."""
    figure.update_layout(
        height=185, showlegend=False,
        margin=dict(l=45, r=5, t=5, b=35), font=dict(size=10),
    )
    figure.update_xaxes(title_font=dict(size=10), tickfont=dict(size=9), nticks=4)
    figure.update_yaxes(title_font=dict(size=10), tickfont=dict(size=9), nticks=4)
    return figure


def show_diagnostics():
    st.header("Vehicle Diagnostics")
    st.caption("Voltesse Dash | " + ("Performance Analysis (database)" if source.USING_DB else "Simulated Performance Analysis"))

    selected = st.session_state.get("selected_session")
    if selected:
        st.info(
            f"Viewing Session {selected['id']} | Date: {selected['date']} | "
            f"Duration: {selected['duration']} | Max Temperature: {selected['max_temp']} °C"
        )
    else:
        st.info("No session selected. Showing the newest session." if source.USING_DB
                else "No session selected. Visit the Sessions page and click View.")

    data = source.diagnostics_data(selected)
    top_cols = st.columns(3, gap="small")
    bottom_cols = st.columns(2, gap="small")

    # Graph 1: Efficiency vs. Speed
    top_cols[0].markdown("**Energy Efficiency vs. Speed**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["speeds"], y=data["efficiency"], mode="lines+markers",
        name="Energy Efficiency", line=dict(color="#D18A24", width=3),
        marker=dict(size=6),
    ))
    fig.update_layout(
        xaxis_title="Vehicle Speed (MPH)",
        yaxis_title="Energy Consumption (Wh/mi)",
        yaxis_range=None if source.USING_DB else [110, 300], template="plotly_white",
    )
    top_cols[0].plotly_chart(compact_chart(fig), width="stretch")

    # Graph 2: Power vs. Motor Temperature
    top_cols[1].markdown("**Power Draw vs. Motor Temperature**")
    fig_power = go.Figure()
    fig_power.add_trace(go.Scatter(
        x=data["motor_temps"], y=data["power_draws"],
        mode="markers", name="Simulated Measurements",
        marker=dict(color="#D18A24", size=9),
    ))
    fig_power.add_trace(go.Scatter(
        x=data["motor_temps"], y=data["trend_power"],
        mode="lines", name="Trend", line=dict(color="#A64B32", width=2),
    ))
    fig_power.update_layout(
        xaxis_title="Motor Temperature (°C)",
        yaxis_title="Power Draw (W)", template="plotly_white",
    )
    top_cols[1].plotly_chart(compact_chart(fig_power), width="stretch")

    # Graph 3: Battery vs. Distance
    top_cols[2].markdown("**Battery Consumption vs. Distance**")
    fig_battery = go.Figure()
    fig_battery.add_trace(go.Scatter(
        x=data["distances"], y=data["battery_levels"],
        mode="lines+markers", name="Battery Remaining",
        line=dict(color="#2E8B57", width=3), marker=dict(size=5),
    ))
    fig_battery.update_layout(
        xaxis_title="Distance Traveled (miles)",
        yaxis_title="Battery Remaining (%)", yaxis=dict(range=[0, 100]),
        template="plotly_white",
    )
    top_cols[2].plotly_chart(compact_chart(fig_battery), width="stretch")

    # Graph 4: Power vs. RPM
    bottom_cols[0].markdown("**Power Draw vs. Motor RPM**")
    fig_rpm = go.Figure()
    fig_rpm.add_trace(go.Scatter(
        x=data["motor_rpms"], y=data["power_values"],
        mode="markers", name="Simulated Measurements",
        marker=dict(color="#B04A76", size=9),
    ))
    fig_rpm.add_trace(go.Scatter(
        x=data["motor_rpms"], y=data["trend_values"],
        mode="lines", name="Power Trend", line=dict(color="#8B3A62", width=3),
    ))
    fig_rpm.update_layout(
        xaxis_title="Motor Speed (RPM)",
        yaxis_title="Power Draw (W)", template="plotly_white",
    )
    bottom_cols[0].plotly_chart(compact_chart(fig_rpm), width="stretch")

    # Graph 5: Temperature rise vs. Time, with the Settings threshold
    bottom_cols[1].markdown("**Motor Temperature Rise Over Time**")
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(
        x=data["time_minutes"], y=data["temp_rise"],
        mode="lines", name="Motor Temperature",
        line=dict(color="#D18A24", width=3),
    ))
    fig_temp.add_hline(
        y=st.session_state.warning_temp, line_dash="dash", line_color="red",
        annotation_text="Warning Limit", annotation_position="top right",
    )
    fig_temp.update_layout(
        xaxis_title="Operation Time (minutes)",
        yaxis_title="Motor Temperature (°C)",
        yaxis=dict(range=[25, max(65, data["peak_temp"] + 5,
                                  st.session_state.warning_temp + 5)]),
        template="plotly_white",
    )
    bottom_cols[1].plotly_chart(compact_chart(fig_temp), width="stretch")
