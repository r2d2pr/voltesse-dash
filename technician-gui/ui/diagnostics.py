"""
Five session-specific performance charts arranged 3 + 2, querying PostgreSQL with fallback.
Exclusively standardized on Imperial units (°F, MPH, miles) with Voltesse cyber pit-wall aesthetics.
"""

import plotly.graph_objects as go
import streamlit as st

from data.db import get_diagnostics_data


def compact_chart(figure):
    """Style charts with Voltesse dark pit-wall aesthetics."""
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
                ⚡ TELEMETRY DIAGNOSTICS & BENCHMARKING
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
                <span class="v-pill v-pill-active">🟢 POSTGRESQL LINKED</span>
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
                <span class="v-pill v-pill-standby">🟡 BENCHMARK PROFILE</span>
                <span style="margin-left: 8px; font-size: 0.8rem; color: #E2E8F0;">
                    PostgreSQL offline or no active session selected. Showing Voltesse benchmark baseline.
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
        annotation_text=f"Warning Limit ({warn_temp}°F)", annotation_position="top right",
    )
    fig_temp.update_layout(
        xaxis_title="Session Elapsed Time (minutes)",
        yaxis_title="Motor Temperature (°F)",
        yaxis=dict(range=[60, max(180, data.get("peak_temp", 140) + 15, warn_temp + 15)]),
    )
    bottom_cols[1].plotly_chart(compact_chart(fig_temp), width="stretch")

    # Diagnostic DTC Fault Code Simulation Console
    render_dtc_console()


def render_dtc_console():
    """Renders the standardized EV Diagnostic Trouble Code (DTC) injection console."""
    st.divider()
    st.markdown(
        """
        <div style="margin-bottom: 10px;">
            <div style="font-size: 1.05rem; font-weight: 800; color: #00F5D4; letter-spacing: 0.04em;">
                ⚡ DIAGNOSTIC TROUBLE CODE (DTC) INJECTION CONSOLE
            </div>
            <p style="margin: 0; padding: 0; font-size: 0.82rem; color: #94A3B8;">
                Inject standardized automotive EV diagnostic faults to validate cluster alerts, safe shutdown routines, and telemetry warnings.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "injected_dtcs" not in st.session_state:
        st.session_state.injected_dtcs = []

    dtc_specs = [
        {
            "code": "P0A38",
            "name": "INVERTER_OVERTEMP",
            "system": "POWERTRAIN",
            "severity": "CRITICAL",
            "desc": "Inverter thermal limit exceeded (≥ 175°F)",
            "action": "Reduce drive output; check cooling pump flow.",
        },
        {
            "code": "P0A80",
            "name": "BATT_CELL_IMBALANCE",
            "system": "HV PACK",
            "severity": "WARNING",
            "desc": "Pack module delta > 120mV across bricks",
            "action": "Schedule cell balancing cycle at bench charger.",
        },
        {
            "code": "C1A20",
            "name": "TPMS_RAPID_DEFLATE_FL",
            "system": "CHASSIS",
            "severity": "CRITICAL",
            "desc": "Front-Left tire pressure drop rate > 0.4 psi/s",
            "action": "Pit immediately; verify tire sidewall integrity.",
        },
        {
            "code": "P0A44",
            "name": "MOTOR_RESOLVER_FAULT",
            "system": "POWERTRAIN",
            "severity": "CRITICAL",
            "desc": "Traction motor rotor phase angular error",
            "action": "Calibrate resolver offset; inspect harness shielding.",
        },
        {
            "code": "C1201",
            "name": "BRAKE_SYSTEM_DEGRADATION",
            "system": "BRAKES",
            "severity": "WARNING",
            "desc": "Blended regen cutback; hydraulic threshold alert",
            "action": "Verify brake fluid level and vacuum booster pressure.",
        },
    ]

    # Quick Inject Buttons
    cols = st.columns(len(dtc_specs))
    for idx, dtc in enumerate(dtc_specs):
        badge_color = "#FF4D6D" if dtc["severity"] == "CRITICAL" else "#FFB800"
        with cols[idx]:
            st.markdown(
                f"<div style='font-size: 0.72rem; font-weight: 700; color: {badge_color}; text-align: center; margin-bottom: 4px;'>"
                f"{dtc['code']} [{dtc['severity']}]</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"⚡ {dtc['name']}", key=f"inject_{dtc['code']}", width="stretch", help=dtc["desc"]):
                # Append if not already present
                existing = [x["code"] for x in st.session_state.injected_dtcs]
                if dtc["code"] not in existing:
                    st.session_state.injected_dtcs.append(dtc)
                    st.rerun()

    # Console Status & Reset Bar
    c_status, c_clear = st.columns([4, 1.2])
    active_count = len(st.session_state.injected_dtcs)
    
    with c_status:
        if active_count == 0:
            st.markdown(
                """
                <div style="background: rgba(0, 245, 212, 0.08); border: 1px solid rgba(0, 245, 212, 0.3); 
                            border-radius: 6px; padding: 8px 14px; margin-top: 10px;">
                    <span class="v-pill v-pill-active">🟢 DTC STATUS: ALL SYSTEMS NOMINAL</span>
                    <span style="margin-left: 10px; font-size: 0.82rem; color: #E2E8F0;">
                        No simulated diagnostic faults injected. Clean vehicle health record.
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="background: rgba(255, 77, 109, 0.12); border: 1px solid rgba(255, 77, 109, 0.4); 
                            border-radius: 6px; padding: 8px 14px; margin-top: 10px;">
                    <span class="v-pill" style="background: rgba(255, 77, 109, 0.3); color: #FF4D6D; border: 1px solid #FF4D6D;">
                        🔴 ACTIVE FAULTS: {active_count} DTC(s) INJECTED
                    </span>
                    <span style="margin-left: 10px; font-size: 0.82rem; color: #FFFFFF;">
                        Simulated EV safety warning active.
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with c_clear:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🧹 Clear All DTCs", key="clear_all_dtcs", width="stretch", disabled=(active_count == 0)):
            st.session_state.injected_dtcs = []
            st.rerun()

    # Active DTC Cards List
    if active_count > 0:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        for dtc in st.session_state.injected_dtcs:
            border_c = "#FF4D6D" if dtc["severity"] == "CRITICAL" else "#FFB800"
            st.markdown(
                f"""
                <div style="background: rgba(13, 22, 26, 0.85); border-left: 4px solid {border_c}; 
                            border-radius: 4px; padding: 10px 14px; margin-bottom: 6px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: 800; color: {border_c}; font-family: Consolas;">
                            [{dtc['code']}] {dtc['name']}
                        </span>
                        <span style="font-size: 0.75rem; color: #94A3B8;">SYSTEM: {dtc['system']}</span>
                    </div>
                    <div style="font-size: 0.82rem; color: #E2E8F0; margin-top: 3px;">
                        {dtc['desc']}
                    </div>
                    <div style="font-size: 0.75rem; color: #5CFFC7; margin-top: 4px;">
                        <strong>Technician Action:</strong> {dtc['action']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

