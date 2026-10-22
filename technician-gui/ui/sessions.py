"""
Recent vehicle session list, timing-board review, interactive replay scrubbing,
and dual-run ghost telemetry overlays querying PostgreSQL.
Standardized on Imperial units (°F, MPH, miles) with Voltesse Pit-Wall command center styling.
"""

import plotly.graph_objects as go
import streamlit as st

from data.db import get_recent_sessions, get_session_telemetry_traces


def compact_chart(figure):
    """Style replay charts with Voltesse dark pit-wall aesthetics."""
    figure.update_layout(
        height=220,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9, color="#E2E8F0")),
        margin=dict(l=45, r=15, t=25, b=30),
        font=dict(size=10, color="#E2E8F0"),
        template="plotly_dark",
        paper_bgcolor="#090E11",
        plot_bgcolor="#070B0D",
    )
    figure.update_xaxes(
        title_font=dict(size=9, color="#94A3B8"),
        tickfont=dict(size=9, color="#E2E8F0"),
        showgrid=True,
        gridcolor="rgba(0, 245, 212, 0.08)",
        zeroline=False,
    )
    figure.update_yaxes(
        title_font=dict(size=9, color="#94A3B8"),
        tickfont=dict(size=9, color="#E2E8F0"),
        showgrid=True,
        gridcolor="rgba(0, 245, 212, 0.08)",
        zeroline=False,
    )
    return figure


def show_sessions():
    st.markdown(
        """
        <div style="margin-bottom: 12px;">
            <h2 style="margin: 0; padding: 0; font-weight: 800; letter-spacing: 0.05em; color: #FFFFFF;">
                ⚡ VEHICLE SESSIONS & TIMING LOG
            </h2>
            <p style="margin: 0; padding: 0; font-size: 0.82rem; color: #94A3B8;">
                Historical vehicle stints and test runs logged into PostgreSQL persistence engine with interactive replay scrubbing.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sessions, is_db = get_recent_sessions(limit=25)

    if is_db:
        st.markdown(
            """
            <div style="background: rgba(0, 245, 212, 0.08); border: 1px solid rgba(0, 245, 212, 0.3); 
                        border-radius: 6px; padding: 6px 12px; margin-bottom: 12px;">
                <span class="v-pill v-pill-active">🟢 POSTGRESQL VEHICLE_SESSION LOG</span>
                <span style="margin-left: 8px; font-size: 0.8rem; color: #E2E8F0;">
                    Live session records loaded from database.
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
                <span class="v-pill v-pill-standby">🟡 BENCH SESSIONS</span>
                <span style="margin-left: 8px; font-size: 0.8rem; color: #E2E8F0;">
                    PostgreSQL offline. Showing Voltesse benchmark session history.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Session Table Header
    headers = st.columns([1, 1.8, 1.2, 1, 1, 1, 1, 1])
    col_names = ["Session", "Date", "Source", "Duration", "Peak Temp", "Top Speed", "Distance", "Action"]
    for col, label in zip(headers, col_names):
        col.markdown(f"<div style='font-size: 0.75rem; font-weight: 700; color: #00F5D4; letter-spacing: 0.06em;'>{label}</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 4px; border-bottom: 1px solid rgba(0, 245, 212, 0.2); margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    for session in sessions:
        cols = st.columns([1, 1.8, 1.2, 1, 1, 1, 1, 1])
        cols[0].markdown(f"**{session['id']}**")
        cols[1].write(session["date"])
        
        src = session.get("source_type", "CAN_BUS")
        pill_class = "v-pill-active" if src in ("CAN_BUS", "RACE") else "v-pill-standby"
        cols[2].markdown(f"<span class='v-pill {pill_class}'>{src}</span>", unsafe_allow_html=True)
        
        cols[3].write(session["duration"])
        cols[4].write(f"{session['max_temp']} °F")
        cols[5].write(f"{session.get('max_speed_mph', 0)} MPH")
        cols[6].write(f"{session.get('total_distance_mi', 0)} mi")
        
        if cols[7].button("Inspect", key=f"view_{session['id']}", help="Load this session into Replay Scrubber and Diagnostics"):
            st.session_state.selected_session = session
            st.rerun()

    # Default to first session if none selected
    if not st.session_state.get("selected_session") and sessions:
        st.session_state.selected_session = sessions[0]

    selected = st.session_state.get("selected_session")
    if selected:
        st.divider()

        # Session Telemetry Traces
        traces, _ = get_session_telemetry_traces(selected)
        total_pts = len(traces["speeds"]) if traces.get("speeds") else 60

        # Session Overview Header
        st.markdown(
            f"""
            <div style="background: linear-gradient(145deg, #0D161A, #080C0E); border: 1px solid #00F5D4; 
                        border-radius: 8px; padding: 14px; margin-bottom: 14px; box-shadow: 0 4px 16px rgba(0, 245, 212, 0.15);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 1.05rem; font-weight: 800; color: #00F5D4;">
                        ⚡ ACTIVE INSPECTION & REPLAY: SESSION {selected['id']}
                    </div>
                    <div>
                        <span class="v-pill v-pill-active">TIMELINE SCRUBBING READY</span>
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 0.85rem; color: #E2E8F0;">
                    <strong>Date:</strong> {selected['date']} &nbsp;|&nbsp; 
                    <strong>Driver:</strong> {selected.get('driver', 'driver')} &nbsp;|&nbsp; 
                    <strong>Duration:</strong> {selected['duration']} &nbsp;|&nbsp; 
                    <strong>Peak Temp:</strong> {selected['max_temp']} °F &nbsp;|&nbsp; 
                    <strong>Top Speed:</strong> {selected.get('max_speed_mph', 0)} MPH &nbsp;|&nbsp; 
                    <strong>Distance:</strong> {selected.get('total_distance_mi', 0)} mi ({selected.get('total_distance_km', 0)} km)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # -------------------------------------------------------------
        # Replay Controls & Ghost Benchmark Selection
        # -------------------------------------------------------------
        st.markdown("<div style='font-size: 0.9rem; font-weight: 800; color: #00F5D4; margin-bottom: 6px;'>🎬 SESSION REPLAY SCRUBBER & GHOST BENCHMARK</div>", unsafe_allow_html=True)
        
        ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1.2, 1.2, 1.5, 3.1])

        # Play / Pause state
        is_playing = st.session_state.get("replay_playing", False)
        btn_label = "⏸ Pause" if is_playing else "▶ Play"
        if ctrl_col1.button(btn_label, width="stretch", key="replay_play_btn"):
            st.session_state.replay_playing = not is_playing
            st.rerun()

        # Playback rate
        rate_choice = ctrl_col2.selectbox("Playback Rate", options=["1x", "2x", "5x"], index=0, key="replay_rate_sel")
        rate_mult = int(rate_choice.replace("x", ""))

        # Ghost Run Selection
        ghost_options = ["None"] + [s["id"] for s in sessions if s["id"] != selected["id"]]
        selected_ghost_id = ctrl_col3.selectbox("Ghost Benchmark Run", options=ghost_options, index=0, key="ghost_run_sel")

        # Ghost traces if selected
        ghost_traces = None
        if selected_ghost_id != "None":
            ghost_traces, _ = get_session_telemetry_traces(selected_ghost_id, total_points=total_pts)

        # Handle Playback Auto-Advance
        curr_idx = st.session_state.get("replay_scrub_idx", 0)
        if is_playing:
            curr_idx = (curr_idx + rate_mult) % total_pts
            st.session_state.replay_scrub_idx = curr_idx

        # Timeline Scrubber Slider
        scrub_idx = st.slider(
            "Scrub Replay Timeline (Frames / Seconds)",
            min_value=0,
            max_value=max(0, total_pts - 1),
            value=min(curr_idx, max(0, total_pts - 1)),
            step=1,
            key="replay_slider",
            help="Drag slider to scrub through recorded telemetry frames.",
        )
        st.session_state.replay_scrub_idx = scrub_idx

        # Calculate live delta readouts against Ghost benchmark
        val_spd = traces["speeds"][scrub_idx] if scrub_idx < len(traces["speeds"]) else 0.0
        val_rpm = traces["rpms"][scrub_idx] if scrub_idx < len(traces["rpms"]) else 0
        val_pwr = traces["powers_kw"][scrub_idx] if scrub_idx < len(traces["powers_kw"]) else 0.0
        val_tmp = traces["motor_temps_f"][scrub_idx] if scrub_idx < len(traces["motor_temps_f"]) else 0.0
        val_thr = traces["throttles"][scrub_idx] if scrub_idx < len(traces["throttles"]) else 0.0
        val_brk = traces["brakes"][scrub_idx] if scrub_idx < len(traces["brakes"]) else 0.0

        d_spd_str = "Live Trace"
        d_pwr_str = "Net Power"
        d_tmp_str = "Core Temp"
        if ghost_traces and scrub_idx < len(ghost_traces.get("speeds", [])):
            g_spd = ghost_traces["speeds"][scrub_idx]
            g_pwr = ghost_traces["powers_kw"][scrub_idx]
            g_tmp = ghost_traces["motor_temps_f"][scrub_idx]

            delta_spd = val_spd - g_spd
            delta_pwr = val_pwr - g_pwr
            delta_tmp = val_tmp - g_tmp

            d_spd_str = f"Δ {delta_spd:+.1f} MPH vs {selected_ghost_id}"
            d_pwr_str = f"Δ {delta_pwr:+.1f} kW vs {selected_ghost_id}"
            d_tmp_str = f"Δ {delta_tmp:+.1f} °F vs {selected_ghost_id}"

        # Snapshot Metric Cards
        m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
        m_c1.metric("Scrubbed Speed", f"{val_spd} MPH", delta=d_spd_str, border=True)
        m_c2.metric("Motor Velocity", f"{val_rpm} RPM", delta="Nominal Sync", delta_color="off", border=True)
        m_c3.metric("Net Power", f"{val_pwr:+.1f} kW", delta=d_pwr_str, border=True)
        m_c4.metric("Motor Core Temp", f"{val_tmp} °F", delta=d_tmp_str, border=True)
        m_c5.metric("Driver Input", f"T {int(val_thr)}% | B {int(val_brk)}%", delta="Demand Overlay", delta_color="off", border=True)

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # -------------------------------------------------------------
        # Synchronized Replay Telemetry Traces with Scrubber Cursor
        # -------------------------------------------------------------
        xs = traces["indices"]

        # Channel 1: Speed & RPM
        st.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #00F5D4;'>CH1: VEHICLE SPEED (MPH) & MOTOR VELOCITY (RPM)</div>", unsafe_allow_html=True)
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=xs, y=traces["speeds"], mode="lines", name=f"{selected['id']} Speed",
            line=dict(color="#00F5D4", width=2.5),
        ))
        if ghost_traces:
            fig1.add_trace(go.Scatter(
                x=ghost_traces["indices"], y=ghost_traces["speeds"], mode="lines",
                name=f"👻 {selected_ghost_id} Ghost Speed",
                line=dict(color="#E2E8F0", width=2.0, dash="dot"),
            ))
        fig1.add_vline(x=scrub_idx, line_width=2, line_dash="dash", line_color="#FF4D6D", annotation_text="Cursor", annotation_position="top left")
        fig1.update_layout(xaxis_title="Timeline Elapsed (Frames)", yaxis_title="Speed (MPH)")
        st.plotly_chart(compact_chart(fig1), width="stretch")

        # Channel 2: Throttle & Brake
        st.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #00F5D4;'>CH2: DRIVER DEMAND (THROTTLE % & BRAKE %)</div>", unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=xs, y=traces["throttles"], mode="lines", name="Throttle %",
            line=dict(color="#00F5A0", width=2.0), fill="tozeroy", fillcolor="rgba(0, 245, 160, 0.12)",
        ))
        fig2.add_trace(go.Scatter(
            x=xs, y=traces["brakes"], mode="lines", name="Brake %",
            line=dict(color="#FF4D6D", width=2.0), fill="tozeroy", fillcolor="rgba(255, 77, 109, 0.15)",
        ))
        if ghost_traces:
            fig2.add_trace(go.Scatter(
                x=ghost_traces["indices"], y=ghost_traces["throttles"], mode="lines",
                name=f"👻 {selected_ghost_id} Throttle",
                line=dict(color="#94A3B8", width=1.5, dash="dot"),
            ))
        fig2.add_vline(x=scrub_idx, line_width=2, line_dash="dash", line_color="#FF4D6D")
        fig2.update_layout(xaxis_title="Timeline Elapsed (Frames)", yaxis_title="Demand (%)", yaxis=dict(range=[0, 105]))
        st.plotly_chart(compact_chart(fig2), width="stretch")

        # Channel 3: Net Power & Motor Temp
        st.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #00F5D4;'>CH3: NET POWER (kW) & MOTOR TEMPERATURE (°F)</div>", unsafe_allow_html=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=xs, y=traces["powers_kw"], mode="lines", name=f"{selected['id']} Power (kW)",
            line=dict(color="#00E5FF", width=2.2),
        ))
        fig3.add_trace(go.Scatter(
            x=xs, y=traces["motor_temps_f"], mode="lines", name=f"{selected['id']} Motor Temp (°F)",
            line=dict(color="#FFB800", width=2.2),
        ))
        if ghost_traces:
            fig3.add_trace(go.Scatter(
                x=ghost_traces["indices"], y=ghost_traces["powers_kw"], mode="lines",
                name=f"👻 {selected_ghost_id} Power",
                line=dict(color="#CBD5E1", width=1.8, dash="dot"),
            ))
        fig3.add_vline(x=scrub_idx, line_width=2, line_dash="dash", line_color="#FF4D6D")
        fig3.update_layout(xaxis_title="Timeline Elapsed (Frames)", yaxis_title="Telemetry Units (kW / °F)")
        st.plotly_chart(compact_chart(fig3), width="stretch")

