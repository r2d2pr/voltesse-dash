"""Telemetry from the Voltesse PostgreSQL database (see db/schema.sql).

Returns the same shapes as data/simulator.py so the pages work with either source.
Charts read the technician views (v_efficiency_by_speed, ...) defined in the schema.
"""

import os
from statistics import StatisticsError, linear_regression

import psycopg
import streamlit as st
from psycopg.rows import dict_row

DB_URL = os.environ.get("VOLTESSE_DB_URL", "")
KM_TO_MILES = 0.621371

SESSIONS_SQL = """
    SELECT s.session_id, s.start_timestamp,
           COALESCE(s.end_timestamp, max(t."timestamp"), s.start_timestamp) - s.start_timestamp AS duration,
           round(max(t.motor_temperature)::numeric, 1) AS max_temp
    FROM vehicle_session s LEFT JOIN telemetry_log t USING (session_id)
    GROUP BY s.session_id
    ORDER BY s.start_timestamp DESC, s.session_id DESC
    LIMIT 20
"""


def _rows(sql, params=()):
    # ponytail: one short connection per query, fine on localhost; use a pool if it ever feels slow
    try:
        with psycopg.connect(DB_URL, row_factory=dict_row, connect_timeout=3) as conn:
            return conn.execute(sql, params).fetchall()
    except psycopg.OperationalError as e:
        st.error(f"Cannot reach the Voltesse database. Is it running?\n\n{e}")
        st.stop()


def _trend(xs, ys):
    """Straight-line fit for the chart trend lines; empty when there are too few points."""
    try:
        slope, intercept = linear_regression(xs, ys)
    except StatisticsError:
        return []
    return [round(slope * x + intercept) for x in xs]


def get_sessions():
    sessions = []
    for row in _rows(SESSIONS_SQL):
        minutes, seconds = divmod(int(row["duration"].total_seconds()), 60)
        sessions.append({
            "id": f"#{row['session_id']}",
            "session_id": row["session_id"],
            "date": row["start_timestamp"].strftime("%b %d, %Y"),
            "duration": f"{minutes:02d}:{seconds:02d}",
            "max_temp": float(row["max_temp"] or 0),
        })
    return sessions


def latest_metrics():
    """Newest reading of the newest session, or None if nothing has been recorded."""
    rows = _rows("""
        SELECT speed_mph, motor_rpm, battery_percent, motor_temperature
        FROM telemetry_log
        WHERE session_id = (SELECT max(session_id) FROM vehicle_session)
        ORDER BY "timestamp" DESC LIMIT 1
    """)
    if not rows:
        return None
    r = rows[0]
    return {
        "speed": round(r["speed_mph"] or 0, 1),
        "rpm": r["motor_rpm"] or 0,
        "battery": round(r["battery_percent"] or 0, 1),
        "temperature": round(r["motor_temperature"] or 0, 1),
    }


def temperature_history():
    """Last 60 seconds of motor temperature for the newest session (seconds into session, °C)."""
    rows = _rows("""
        SELECT seconds_into_session, motor_temperature
        FROM v_temperature_over_time
        WHERE session_id = (SELECT max(session_id) FROM vehicle_session)
          AND seconds_into_session >= (
              SELECT max(seconds_into_session) - 60 FROM v_temperature_over_time
              WHERE session_id = (SELECT max(session_id) FROM vehicle_session))
    """)
    return [r["seconds_into_session"] for r in rows], [r["motor_temperature"] for r in rows]


def diagnostics_data(session=None):
    """The five chart datasets for one session (the newest one if none is selected)."""
    if session:
        sid = session["session_id"]
    else:
        newest = _rows("SELECT max(session_id) AS sid FROM vehicle_session")[0]["sid"]
        sid = newest or 0

    eff = _rows("SELECT speed_bucket_mph AS x, wh_per_mile AS y FROM v_efficiency_by_speed "
                "WHERE session_id = %s ORDER BY 1", (sid,))
    temp = _rows("SELECT temperature_bucket_c AS x, avg_power_watts AS y FROM v_power_by_temperature "
                 "WHERE session_id = %s ORDER BY 1", (sid,))
    batt = _rows("SELECT trip_distance_km AS x, battery_percent AS y FROM v_battery_over_distance "
                 "WHERE session_id = %s ORDER BY 1", (sid,))
    rpm = _rows("SELECT rpm_bucket AS x, avg_power_watts AS y FROM v_power_by_rpm "
                "WHERE session_id = %s ORDER BY 1", (sid,))
    rise = _rows("SELECT seconds_into_session AS x, motor_temperature AS y FROM v_temperature_over_time "
                 "WHERE session_id = %s", (sid,))

    motor_temps, power_draws = [r["x"] for r in temp], [float(r["y"]) for r in temp]
    motor_rpms, power_values = [r["x"] for r in rpm], [float(r["y"]) for r in rpm]
    temp_rise = [r["y"] for r in rise]
    return {
        "speeds": [r["x"] for r in eff], "efficiency": [float(r["y"]) for r in eff],
        "motor_temps": motor_temps, "power_draws": power_draws,
        "trend_power": _trend(motor_temps, power_draws),
        "distances": [round(r["x"] * KM_TO_MILES, 2) for r in batt],
        "battery_levels": [r["y"] for r in batt],
        "motor_rpms": motor_rpms, "power_values": power_values,
        "trend_values": _trend(motor_rpms, power_values),
        "time_minutes": [round(r["x"] / 60, 2) for r in rise], "temp_rise": temp_rise,
        "peak_temp": max(temp_rise, default=0),
    }
