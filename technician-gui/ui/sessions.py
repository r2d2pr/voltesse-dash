"""Recent session list and View selection shared with Diagnostics."""

import streamlit as st

from data.simulator import SESSIONS


def show_sessions():
    st.title("Recent Sessions")
    st.caption("Voltesse Dash | Simulated Session History")

    headers = st.columns([1, 2, 1, 1, 1])
    for col, label in zip(headers, ["Session", "Date", "Duration", "Max Temp", "Action"]):
        col.markdown(f"**{label}**")

    for session in SESSIONS:
        cols = st.columns([1, 2, 1, 1, 1])
        cols[0].write(session["id"])
        cols[1].write(session["date"])
        cols[2].write(session["duration"])
        cols[3].write(f"{session['max_temp']} °C")
        if cols[4].button("View", key=f"view_{session['id']}"):
            st.session_state.selected_session = session

    selected = st.session_state.get("selected_session")
    if selected:
        st.subheader(f"Selected Session: {selected['id']}")
        st.info(
            f"Date: {selected['date']} | Duration: {selected['duration']} | "
            f"Max Temperature: {selected['max_temp']} °C"
        )
        st.caption("Open Diagnostics to review the selected session's simulated charts.")
