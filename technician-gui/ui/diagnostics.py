"""
Five session-specific performance charts arranged 3 + 2, querying PostgreSQL with fallback.
Exclusively standardized on Imperial units (°F, MPH, miles) with Mercedes-AMG F1 aesthetics.
"""

import plotly.graph_objects as go
import streamlit as st

from data.db import get_diagnostics_data


def compact_chart(figure):
    """Style charts with Mercedes-AMG F1 dark pit-wall aesthetics."""
    figure.update_layout(
        height=240,
        showlegend=False,
        margin=dict(l=45, r=15, t=15, b=35),
        font=dict(size=10, color="#E2E8F0"),
        template="plotly_dark",
        paper_bgcolor="#090E11",
        plot_bgcolor="#070B0D",
    )
    figure.update_xaxes(
        title_font=dict(size=10, color="#94A3B8"),
        tickfont=dict(size=9, color="#E2E8F0"),
        showgrid=True,
        gridcolor="rgba(0, 245, 212, 0.08)",
        zeroline=False,
        nticks=5,
    )
    figure.update_yaxes(
        title_font=dict(size=10, color="#94A3B8"),
        tickfont=dict(size=9, color="#E2E8F0"),
        showgrid=True,
        gridcolor="rgba(0, 245, 212, 0.08)",
        zeroline=False,
        nticks=5,
    )
    return figure


def show_diagnostics():
    st.markdown(
        """
        <div style="margin-bottom: 12px;">
            <h2 style="margin: 0; padding: 0; font-weight: 800; letter-spacing: 0.05em; color: #FFFFFF;">
                🏎️ TELEMETRY DIAGNOSTICS & BENCHMARKING
            </h2>
            <p style="margin: 0; padding: 0; font-size: 0.82rem; color: #94A3B8;">
                Historical and session-specific vehicle performance curves derived from PostgreSQL persistence logs.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected = st.session_state.get("selected_session")
    data, is_db = get_diagnostics_data(selected)

    if is_db:
        st.markdown(
            """
            <div style="background: rgba(0, 245, 212, 0.08); border: 1px solid rgba(0, 245, 212, 0.3); 
                        border-radius: 6px; padding: 6px 12px; margin-bottom: 12px;">
                <span class="f1-pill f1-pill-active">🟢 POSTGRESQL LINKED</span>
                <span style="margin-left: 8px; font-size: 0.8rem; color: #E2E8F0;">
                    Analyzing high-resolution telemetry frames from vehicle session database.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background: rgba(255, 184, 0, 0.08); border: 1px solid rgba(255, 184, 0, 0.3); 
                        border-radius: 6px; padding: 6px 12px; margin-bottom: 12px;">
                <span class="f1-pill f1-pill-standby">🟡 BENCHMARK PROFILE</span>
                <span style="margin-left: 8px; font-size: 0.8rem; color: #E2E8F0;">
                    PostgreSQL offline or no active session selected. Showing Mercedes-AMG F1 benchmark baseline.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if selected:
        st.info(
            f"Active Session: {selected['id']} | Date: {selected['date']} | "
            f"Duration: {selected['duration']} | Peak Thermal: {selected['max_temp']} °F | "
            f"Max Speed: {selected.get('max_speed_mph', 0)} MPH | Distance: {selected.get('total_distance_mi', 0)} mi"
        )
    else:
        st.caption("Tip: Select a specific run in the **Sessions** channel to inspect individual vehicle telemetry curves.")

    warn_temp = st.session_state.get("warning_temp", 160)

    top_cols = st.columns(3, gap="medium")
    bottom_cols = st.columns(2, gap="medium")

    # Graph 1: Efficiency vs. Speed
    top_cols[0].markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #00F5D4;'>⚡ ENERGY EFFICIENCY VS. SPEED</div>", unsafe_allow_html=True)
    fig_eff = go.Figure()
    fig_eff.add_trace(go.Scatter(
        x=data["speeds"], y=data["efficiency"], mode="lines+markers",
        name="Energy Efficiency", line=dict(color="#00F5D4", width=2.5),
        marker=dict(size=4, color="#5CFFC7"),
    ))
    fig_eff.update_layout(
        xaxis_title="Vehicle Speed (MPH)",
        yaxis_title="Energy Consumption (Wh/mi)",
    )
    top_cols[0].plotly_chart(compact_chart(fig_eff), width="stretch")

    # Graph 2: Power vs. Motor Temperature
    top_cols[1].markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #00F5D4;'>🔥 POWER DRAW VS. MOTOR TEMP</div>", unsafe_allow_html=True)
    fig_power = go.Figure()
    fig_power.add_trace(go.Scatter(
        x=data["motor_temps"], y=data["power_draws"],
        mode="markers", name="Telemetry Points",
        marker=dict(color="#00E5FF", size=5, opacity=0.7),
    ))
    fig_power.add_trace(go.Scatter(
        x=data["motor_temps"], y=data["trend_power"],
        mode="lines", name="Trend", line=dict(color="#00F5D4", width=2.5),
    ))
    fig_power.update_layout(
        xaxis_title="Motor Temperature (°F)",
        yaxis_title="Power Draw (W)",
    )
    top_cols[1].plotly_chart(compact_chart(fig_power), width="stretch")

    # Graph 3: Battery vs. Distance
    top_cols[2].markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #00F5D4;'>🔋 BATTERY DEPLETION VS. DISTANCE</div>", unsafe_allow_html=True)
    fig_battery = go.Figure()
    fig_battery.add_trace(go.Scatter(
        x=data["distances"], y=data["battery_levels"],
        mode="lines+markers", name="Battery SoC",
        line=dict(color="#00F5A0", width=2.5), marker=dict(size=4),
    ))
    fig_battery.update_layout(
        xaxis_title="Distance Traveled (miles)",
        yaxis_title="Battery SoC (%)", yaxis=dict(range=[0, 105]),
    )
    top_cols[2].plotly_chart(compact_chart(fig_battery), width="stretch")

    # Graph 4: Power vs. RPM
    bottom_cols[0].markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #00F5D4;'>⚡ POWER DRAW VS. MOTOR RPM</div>", unsafe_allow_html=True)
    fig_rpm = go.Figure()
    fig_rpm.add_trace(go.Scatter(
        x=data["motor_rpms"], y=data["power_values"],
        mode="markers", name="Telemetry Points",
        marker=dict(color="#FFB800", size=5, opacity=0.7),
    ))
    fig_rpm.add_trace(go.Scatter(
        x=data["motor_rpms"], y=data["trend_values"],
        mode="lines", name="Power Trend", line=dict(color="#FFA000", width=2.5),
    ))
    fig_rpm.update_layout(
        xaxis_title="Motor Velocity (RPM)",
        yaxis_title="Power Draw (W)",
    )
    bottom_cols[0].plotly_chart(compact_chart(fig_rpm), width="stretch")

    # Graph 5: Temperature rise vs. Time with Imperial Warning limit
    bottom_cols[1].markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #00F5D4;'>🌡️ MOTOR THERMAL RISE OVER TIME</div>", unsafe_allow_html=True)
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(
        x=data["time_minutes"], y=data["temp_rise"],
        mode="lines", name="Motor Temperature",
        line=dict(color="#FF4D6D", width=2.5),
    ))
    fig_temp.add_hline(
        y=warn_temp, line_dash="dash", line_color="#FF4D6D",
        annotation_text=f"Race Warning Limit ({warn_temp}°F)", annotation_position="top right",
    )
    fig_temp.update_layout(
        xaxis_title="Session Elapsed Time (minutes)",
        yaxis_title="Motor Temperature (°F)",
        yaxis=dict(range=[60, max(180, data.get("peak_temp", 140) + 15, warn_temp + 15)]),
    )
    bottom_cols[1].plotly_chart(compact_chart(fig_temp), width="stretch")
