"""
Voltesse Telemetry Command Center (v5.0.0).

Live vehicle telemetry streamed directly from PostgreSQL 16 persistence engine.
Interactive simulation sliders are completely deprecated in v5.0.0.
Telemetry is refreshed in real time via automated 1-second Streamlit fragments.
Optimized with fixed axis bounds and uirevision for rock-solid, stutter-free live rendering.
"""

from datetime import datetime, timezone
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from data.db import (
    get_live_metrics,
    get_live_telemetry_traces,
    get_live_temperature_history,
)


def render_live_telemetry_content():
    """Inner telemetry content rendered on every fragment pulse."""
    values, is_db = get_live_metrics()
    traces, traces_is_db = get_live_telemetry_traces(limit=60)

    # 1. Telemetry Link Status Header
    is_active = values.get("is_active", False)
    packet_age = values.get("packet_age_sec", 999.0)
    session_id = values.get("session_id", "N/A")
    log_id = values.get("log_id", "0")
    drive_mode = values.get("drive_mode", "DRIVE")
    gear = values.get("gear", "D")
    trans_mode = values.get("transmission_mode", "AUTO")

    if is_db and is_active:
        st.markdown(
            f"""
            <div style="background: rgba(0, 245, 212, 0.08); border: 1px solid rgba(0, 245, 212, 0.4); 
                        border-radius: 6px; padding: 8px 14px; margin-bottom: 14px; display: flex; 
                        justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span class="v-pill v-pill-active">🟢 TELEMETRY LINK: ACTIVE (CAN-0)</span>
                    <span style="margin-left: 10px; font-size: 0.82rem; font-weight: 600; color: #E2E8F0;">
                        PACKET AGE: <strong style="color: #00F5D4;">{packet_age:.1f}s</strong> &nbsp;|&nbsp; 
                        FRAME ID: <strong style="color: #FFFFFF;">#{log_id}</strong> &nbsp;|&nbsp; 
                        SESSION: <strong style="color: #00F5D4;">#{session_id}</strong>
                    </span>
                </div>
                <div>
                    <span class="v-pill v-pill-active">MODE: {drive_mode}</span>
                    <span class="v-pill v-pill-active" style="margin-left: 6px;">TRANS: {gear} [{trans_mode}]</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif is_db and not is_active:
        age_display = f"{int(packet_age)}s" if packet_age < 3600 else f"{int(packet_age // 60)}m"
        st.markdown(
            f"""
            <div style="background: rgba(255, 184, 0, 0.08); border: 1px solid rgba(255, 184, 0, 0.4); 
                        border-radius: 6px; padding: 8px 14px; margin-bottom: 14px; display: flex; 
                        justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span class="v-pill v-pill-standby">🟠 TELEMETRY LINK: STANDBY</span>
                    <span style="margin-left: 10px; font-size: 0.82rem; font-weight: 600; color: #E2E8F0;">
                        LAST PACKET: <strong style="color: #FFB800;">{age_display} AGO</strong> &nbsp;|&nbsp; 
                        SESSION: <strong style="color: #FFFFFF;">#{session_id}</strong> &nbsp;|&nbsp; 
                        STATUS: VEHICLE PARKED / BENCH IDLE
                    </span>
                </div>
                <div>
                    <span class="v-pill v-pill-standby">AWAITING CAN FRAME</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background: rgba(255, 77, 109, 0.08); border: 1px solid rgba(255, 77, 109, 0.4); 
                        border-radius: 6px; padding: 8px 14px; margin-bottom: 14px; display: flex; 
                        justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span class="v-pill v-pill-alert">🔴 TELEMETRY LINK: DISCONNECTED</span>
                    <span style="margin-left: 10px; font-size: 0.82rem; font-weight: 600; color: #E2E8F0;">
                        POSTGRESQL RECONNECTING... (SHOWING BENCH BASELINE)
                    </span>
                </div>
                <div>
                    <span class="v-pill v-pill-alert">DB OFFLINE</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Critical Warning Strip
    mot_temp = values["motor_temp_f"]
    warn_temp = st.session_state.get("warning_temp", 160)
    battery_soc = values["battery"]
    warn_battery = st.session_state.get("warning_battery", 20)

    is_hot = mot_temp >= warn_temp
    is_low_soc = battery_soc <= warn_battery

    if is_hot:
        st.error(f"🚨 CRITICAL THERMAL LIMIT: Motor Core Temperature {mot_temp:.1f} °F exceeds calibrated threshold ({warn_temp} °F)!")
    if is_low_soc:
        st.warning(f"⚠️ LOW ENERGY ALERT: Battery State-of-Charge at {battery_soc:.1f}% (Limit: {warn_battery}%)!")

    # 3. Primary 6-Card Telemetry Strip
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    # Card 1: Speed
    c1.metric(
        label="Vehicle Speed",
        value=f"{values['speed']} MPH",
        delta=f"{trans_mode} [{gear}]",
        delta_color="off",
    )

    # Card 2: Motor RPM
    c2.metric(
        label="Motor Velocity",
        value=f"{values['rpm']:,} RPM",
        delta=f"Mode: {drive_mode}",
        delta_color="off",
    )

    # Card 3: Battery SoC
    c3.metric(
        label="Battery Pack SoC",
        value=f"{values['battery']}%",
        delta=f"Range: {values['est_range_mi']} mi",
        delta_color="off" if not is_low_soc else "inverse",
    )

    # Card 4: Net Power Flow
    power_kw = values["power_kw"]
    c4.metric(
        label="Net Power Flow",
        value=f"{power_kw:+.1f} kW",
        delta=f"{values['voltage']:.0f}V • {values['current']:+.1f}A",
        delta_color="off",
    )

    # Card 5: Driver Input
    c5.metric(
        label="Driver Demand",
        value=f"THR {values['throttle_pct']:.0f}%",
        delta=f"BRK {values['brake_pct']:.0f}%",
        delta_color="off",
    )

    # Card 6: Motor Core Thermal
    temp_tag = "HOT" if mot_temp >= 195 else ("WARM" if mot_temp >= 160 else "OK")
    c6.metric(
        label="Motor Core Temp",
        value=f"{mot_temp:.1f} °F",
        delta=f"Status: {temp_tag}",
        delta_color="off" if not is_hot else "inverse",
    )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 4. Synchronized Telemetry Traces (Stutter-Free Architecture)
    st.subheader("Real-Time Telemetry Traces")

    if traces_is_db and len(traces.get("indices", [])) >= 3:
        raw_indices = traces["indices"]
        num_pts = len(raw_indices)
        # Relative rolling time window in seconds: rightmost point is 0s (now), earlier points are negative seconds
        time_seconds = [- (num_pts - 1 - i) for i in range(num_pts)]

        speeds = traces["speeds"]
        rpms = traces["rpms"]
        throttles = traces["throttles"]
        brakes = traces["brakes"]
        powers = traces["powers_kw"]

        # Upper Chart: Velocity (MPH) & Motor Velocity (RPM) Dual-Axis Trace
        fig_speed = make_subplots(specs=[[{"secondary_y": True}]])
        fig_speed.add_trace(
            go.Scatter(
                x=time_seconds, y=speeds, name="Speed (MPH)",
                line=dict(color="#00F5D4", width=2.5),
            ),
            secondary_y=False,
        )
        fig_speed.add_trace(
            go.Scatter(
                x=time_seconds, y=rpms, name="Motor RPM",
                line=dict(color="#E2E8F0", width=1.5, dash="dot"),
            ),
            secondary_y=True,
        )
        fig_speed.update_layout(
            title=dict(text="SPEED & MOTOR VELOCITY TRACE", font=dict(size=12, color="#00F5D4")),
            height=260,
            template="plotly_dark",
            paper_bgcolor="#090E11",
            plot_bgcolor="#070B0D",
            margin=dict(l=50, r=50, t=35, b=25),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
            hovermode="x unified",
            uirevision="telemetry_stream",
            transition=dict(duration=0),
        )
        fig_speed.update_xaxes(
            range=[-59, 1],
            fixedrange=True,
            showgrid=True,
            gridcolor="rgba(0, 245, 212, 0.08)",
            ticksuffix="s",
            nticks=7,
        )
        fig_speed.update_yaxes(
            title_text="Speed (MPH)",
            range=[0, 120],
            fixedrange=True,
            showgrid=True,
            gridcolor="rgba(0, 245, 212, 0.08)",
            secondary_y=False,
        )
        fig_speed.update_yaxes(
            title_text="Motor RPM",
            range=[0, 8500],
            fixedrange=True,
            showgrid=False,
            secondary_y=True,
        )
        st.plotly_chart(
            fig_speed,
            key="chart_live_speed",
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )

        # Lower Chart: Driver Demand (Throttle/Brake %) & Net Power Flow (kW)
        fig_demand = make_subplots(specs=[[{"secondary_y": True}]])
        fig_demand.add_trace(
            go.Scatter(
                x=time_seconds, y=throttles, name="Throttle %",
                line=dict(color="#00F5A0", width=2),
                fill="tozeroy", fillcolor="rgba(0, 245, 160, 0.15)",
            ),
            secondary_y=False,
        )
        fig_demand.add_trace(
            go.Scatter(
                x=time_seconds, y=brakes, name="Brake %",
                line=dict(color="#FF4D6D", width=2),
                fill="tozeroy", fillcolor="rgba(255, 77, 109, 0.25)",
            ),
            secondary_y=False,
        )
        fig_demand.add_trace(
            go.Scatter(
                x=time_seconds, y=powers, name="Power (kW)",
                line=dict(color="#00E5FF", width=2),
            ),
            secondary_y=True,
        )
        fig_demand.update_layout(
            title=dict(text="DRIVER DEMAND & NET POWER FLOW", font=dict(size=12, color="#00F5D4")),
            height=260,
            template="plotly_dark",
            paper_bgcolor="#090E11",
            plot_bgcolor="#070B0D",
            margin=dict(l=50, r=50, t=35, b=25),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
            hovermode="x unified",
            uirevision="telemetry_stream",
            transition=dict(duration=0),
        )
        fig_demand.update_xaxes(
            range=[-59, 1],
            fixedrange=True,
            showgrid=True,
            gridcolor="rgba(0, 245, 212, 0.08)",
            ticksuffix="s",
            nticks=7,
        )
        fig_demand.update_yaxes(
            title_text="Demand (%)",
            range=[-2, 102],
            fixedrange=True,
            showgrid=True,
            gridcolor="rgba(0, 245, 212, 0.08)",
            secondary_y=False,
        )
        fig_demand.update_yaxes(
            title_text="Power (kW)",
            range=[-30, 150],
            fixedrange=True,
            showgrid=False,
            secondary_y=True,
        )
        st.plotly_chart(
            fig_demand,
            key="chart_live_demand",
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )
    else:
        # Fallback Temperature Trace (Rock-Solid Fixed Range)
        times, temps, _ = get_live_temperature_history(seconds=60)
        num_pts = len(times)
        rel_times = [- (num_pts - 1 - i) for i in range(num_pts)]

        fig_fallback = go.Figure()
        fig_fallback.add_trace(go.Scatter(
            x=rel_times, y=temps, mode="lines+markers", name="Motor Temp (°F)",
            line=dict(color="#00F5D4", width=3), marker=dict(size=4),
        ))
        fig_fallback.add_hline(
            y=warn_temp, line_dash="dash", line_color="#FF4D6D",
            annotation_text=f"Warning Limit ({warn_temp}°F)", annotation_position="top right",
        )
        fig_fallback.update_layout(
            title=dict(text="MOTOR CORE TEMPERATURE TREND", font=dict(size=12, color="#00F5D4")),
            height=300,
            template="plotly_dark",
            paper_bgcolor="#090E11",
            plot_bgcolor="#070B0D",
            margin=dict(l=50, r=50, t=35, b=25),
            uirevision="telemetry_stream",
            transition=dict(duration=0),
        )
        fig_fallback.update_xaxes(
            range=[-59, 1],
            fixedrange=True,
            showgrid=True,
            gridcolor="rgba(0, 245, 212, 0.08)",
            ticksuffix="s",
            nticks=7,
        )
        fig_fallback.update_yaxes(
            range=[60, max(210, warn_temp + 20)],
            fixedrange=True,
            showgrid=True,
            gridcolor="rgba(0, 245, 212, 0.08)",
            title_text="Motor Temp (°F)",
        )
        st.plotly_chart(
            fig_fallback,
            key="chart_live_fallback",
            width="stretch",
            config={"displayModeBar": False, "responsive": True},
        )

    st.divider()

    # 5. Powertrain & High-Voltage Detailed Matrix
    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown(
            """
            <div style="font-size: 0.85rem; font-weight: 700; color: #00F5D4; letter-spacing: 0.08em; margin-bottom: 8px;">
                ⚡ THERMAL TELEMETRY MATRIX (°F)
            </div>
            """,
            unsafe_allow_html=True,
        )
        t_col1, t_col2 = st.columns(2)
        t_col1.metric("Motor Core", f"{values['motor_temp_f']} °F", border=True)
        t_col2.metric("Power Inverter", f"{values['inverter_temp_f']} °F", border=True)
        t_col1.metric("Battery Pack", f"{values['battery_temp_f']} °F", border=True)
        t_col2.metric("Warning Threshold", f"{warn_temp} °F", border=True)

    with m2:
        st.markdown(
            """
            <div style="font-size: 0.85rem; font-weight: 700; color: #00F5D4; letter-spacing: 0.08em; margin-bottom: 8px;">
                ⚡ HIGH-VOLTAGE PACK BUS
            </div>
            """,
            unsafe_allow_html=True,
        )
        h_col1, h_col2 = st.columns(2)
        h_col1.metric("Pack Voltage", f"{values['voltage']} V", border=True)
        h_col2.metric("Current Draw", f"{values['current']:+.1f} A", border=True)
        h_col1.metric("Gross Power", f"{values['power_w']:,} W", border=True)
        h_col2.metric("SoC Status", f"{values['battery']}%", border=True)

    with m3:
        st.markdown(
            """
            <div style="font-size: 0.85rem; font-weight: 700; color: #00F5D4; letter-spacing: 0.08em; margin-bottom: 8px;">
                🏎️ CHASSIS & VEHICLE DYNAMICS
            </div>
            """,
            unsafe_allow_html=True,
        )
        d_col1, d_col2 = st.columns(2)
        d_col1.metric("Steering Angle", f"{values['steering_angle']}°", border=True)
        d_col2.metric("Trip Odometer", f"{values['trip_mi']} mi", border=True)
        d_col1.metric("Drive Mode", f"{drive_mode}", border=True)
        d_col2.metric("Gear / Ratio", f"{gear} ({trans_mode})", border=True)


@st.fragment(run_every="1s")
def render_live_telemetry_streaming():
    """Fragment re-executing automatically every 1 second without page flicker."""
    render_live_telemetry_content()


@st.fragment
def render_live_telemetry_paused():
    """Fragment when stream is manually paused."""
    render_live_telemetry_content()


def show_live():
    """Main live telemetry command center."""
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.8rem;">⚡</span>
                <div>
                    <h2 style="margin: 0; padding: 0; font-weight: 800; letter-spacing: 0.05em; color: #FFFFFF;">
                        LIVE TELEMETRY COMMAND
                    </h2>
                    <p style="margin: 0; padding: 0; font-size: 0.82rem; color: #94A3B8;">
                        Direct PostgreSQL 16 Persistence Engine Telemetry Feed (Imperial °F / MPH / mi)
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h_col2:
        is_streaming = st.toggle(
            "⚡ Live Stream (1s)",
            value=st.session_state.get("live_stream_active", True),
            help="Toggle automatic 1-second telemetry refresh from PostgreSQL.",
        )
        st.session_state["live_stream_active"] = is_streaming

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    if is_streaming:
        render_live_telemetry_streaming()
    else:
        st.info("⏸️ Telemetry stream is paused. Click 'Live Stream' toggle to resume 1s auto-refresh.")
        render_live_telemetry_paused()
