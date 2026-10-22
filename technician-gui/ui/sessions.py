"""
Recent vehicle session list and timing-board review querying PostgreSQL.
Standardized on Imperial units (°F, MPH, miles) with Voltesse timing board styling.
"""

import streamlit as st

from data.db import get_recent_sessions


def show_sessions():
    st.markdown(
        """
        <div style="margin-bottom: 12px;">
            <h2 style="margin: 0; padding: 0; font-weight: 800; letter-spacing: 0.05em; color: #FFFFFF;">
                ⚡ VEHICLE SESSIONS & TIMING LOG
            </h2>
            <p style="margin: 0; padding: 0; font-size: 0.82rem; color: #94A3B8;">
                Historical vehicle stints and test runs logged into PostgreSQL persistence engine.
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
        
        if cols[7].button("Inspect", key=f"view_{session['id']}", help="Load this session into Diagnostics charts"):
            st.session_state.selected_session = session
            st.rerun()

    selected = st.session_state.get("selected_session")
    if selected:
        st.divider()
        st.markdown(
            f"""
            <div style="background: linear-gradient(145deg, #0D161A, #080C0E); border: 1px solid #00F5D4; 
                        border-radius: 8px; padding: 14px; box-shadow: 0 4px 16px rgba(0, 245, 212, 0.15);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 1rem; font-weight: 800; color: #00F5D4;">
                        ACTIVE INSPECTION: SESSION {selected['id']}
                    </div>
                    <div>
                        <span class="v-pill v-pill-active">READY FOR TELEMETRY ANALYSIS</span>
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
                <div style="margin-top: 6px; font-size: 0.78rem; color: #94A3B8;">
                    Switch to the <strong>Diagnostics</strong> channel in the sidebar to view full synchronized curves for this session.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
