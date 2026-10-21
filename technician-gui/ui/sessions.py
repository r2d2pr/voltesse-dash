"""Recent session list and View selection shared with Diagnostics via PostgreSQL."""

import streamlit as st

from data.db import get_recent_sessions


def show_sessions():
    st.title("Vehicle Sessions")
    sessions, is_db = get_recent_sessions(limit=25)

    if is_db:
        st.caption("Voltesse Dash | 🟢 Connected to PostgreSQL — Live Session Log")
    else:
        st.caption("Voltesse Dash | 🟡 PostgreSQL Offline — Showing Simulated Session History")

    headers = st.columns([1, 2, 1, 1, 1, 1, 1])
    for col, label in zip(headers, ["Session", "Date", "Source", "Duration", "Max Temp", "Max Speed", "Action"]):
        col.markdown(f"**{label}**")

    for session in sessions:
        cols = st.columns([1, 2, 1, 1, 1, 1, 1])
        cols[0].write(session["id"])
        cols[1].write(session["date"])
        cols[2].write(session.get("source_type", "CAN_BUS"))
        cols[3].write(session["duration"])
        cols[4].write(f"{session['max_temp']} °C")
        cols[5].write(f"{session.get('max_speed_mph', 0)} MPH")
        if cols[6].button("View", key=f"view_{session['id']}"):
            st.session_state.selected_session = session

    selected = st.session_state.get("selected_session")
    if selected:
        st.divider()
        st.subheader(f"Selected Session: {selected['id']}")
        st.info(
            f"Date: {selected['date']} | Source: {selected.get('source_type', 'CAN_BUS')} | "
            f"Duration: {selected['duration']} | Max Temperature: {selected['max_temp']} °C | "
            f"Max Speed: {selected.get('max_speed_mph', 0)} MPH | Total Distance: {selected.get('total_distance_km', 0)} km"
        )
        st.caption("Open Diagnostics in the sidebar to review this session's telemetry performance charts.")
