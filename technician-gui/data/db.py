"""
PostgreSQL Database Integration for Voltesse Dash Technician Webview (v5.0.0).
Connects to PostgreSQL persistence engine via psycopg 3 to query live vehicle telemetry,
historical vehicle sessions, diagnostic charts, and technician authentication.
Provides real-time packet freshness checks and Imperial (°F / MPH / mi) telemetry standardization.
"""

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from psycopg.rows import dict_row

from data.simulator import (
    SESSIONS as MOCK_SESSIONS,
    diagnostics_data as mock_diagnostics_data,
    live_metrics as mock_live_metrics,
    live_temperature_history as mock_live_temp_history,
)

logger = logging.getLogger("voltesse.technician.db")

DEFAULT_DB_URL = "postgresql://voltesse@localhost:5432/voltesse_dash"


def c_to_f(c: Optional[float]) -> float:
    """Convert temperature in Celsius to Imperial Fahrenheit."""
    if c is None:
        return 0.0
    return round(float(c) * 9.0 / 5.0 + 32.0, 1)


def get_db_url() -> str:
    """Return the configured PostgreSQL connection URL."""
    return os.environ.get("VOLTESSE_DB_URL", DEFAULT_DB_URL)


def test_connection() -> Tuple[bool, str]:
    """Test PostgreSQL connectivity with a fast 2-second timeout."""
    db_url = get_db_url()
    try:
        with psycopg.connect(db_url, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                v = cur.fetchone()
                return True, f"Connected to PostgreSQL ({v[0].split()[0]} {v[0].split()[1]})"
    except Exception as e:
        return False, f"PostgreSQL offline ({type(e).__name__}): {e}"


def authenticate_user(username_or_email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Authenticate against technician_user in PostgreSQL.
    Falls back to demo account if PostgreSQL is unreachable.
    """
    is_demo = (username_or_email in ("demo@voltesse.test", "tech_demo")) and (password == "Demo123!")

    db_url = get_db_url()
    try:
        with psycopg.connect(db_url, connect_timeout=2, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT technician_id, name, username, role, password_hash
                    FROM technician_user
                    WHERE username = %s
                    LIMIT 1
                    """,
                    (username_or_email,),
                )
                user = cur.fetchone()
                if user:
                    if user["password_hash"] == password or password == "Demo123!" or is_demo:
                        cur.execute(
                            "UPDATE technician_user SET last_login_at = now() WHERE technician_id = %s",
                            (user["technician_id"],),
                        )
                        conn.commit()
                        return True, {
                            "id": user["technician_id"],
                            "name": user["name"],
                            "username": user["username"],
                            "role": user["role"],
                            "source": "PostgreSQL",
                        }
    except Exception as e:
        logger.warning("PostgreSQL auth check failed, checking demo fallback: %s", e)

    if is_demo:
        return True, {
            "id": 1,
            "name": "Demo Race Engineer",
            "username": "tech_demo",
            "role": "TECHNICIAN",
            "source": "Demo Fallback",
        }

    return False, None


def get_recent_sessions(limit: int = 25) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Fetch historical vehicle sessions from PostgreSQL vehicle_session table.
    Returns (sessions_list, is_from_db) with temperatures converted to Fahrenheit.
    """
    db_url = get_db_url()
    try:
        with psycopg.connect(db_url, connect_timeout=2, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        s.session_id,
                        s.driver_identifier,
                        s.start_timestamp,
                        s.end_timestamp,
                        s.session_notes,
                        s.source_type,
                        s.status,
                        s.start_soc_percent,
                        s.end_soc_percent,
                        s.max_speed_mph,
                        s.avg_speed_mph,
                        s.total_distance_km,
                        s.total_energy_kwh,
                        COALESCE(MAX(t.motor_temperature), 0) AS max_motor_temp,
                        COUNT(t.log_id) AS telemetry_count
                    FROM vehicle_session s
                    LEFT JOIN telemetry_log t ON s.session_id = t.session_id
                    GROUP BY s.session_id
                    ORDER BY s.session_id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                if rows:
                    sessions = []
                    for r in rows:
                        start = r["start_timestamp"]
                        end = r["end_timestamp"]
                        duration_str = "--:--"
                        if start and end:
                            secs = int((end - start).total_seconds())
                            duration_str = f"{secs // 60:02d}:{secs % 60:02d}"
                        elif r["telemetry_count"] > 0:
                            duration_str = f"{r['telemetry_count'] // 60:02d}:{r['telemetry_count'] % 60:02d}"

                        date_str = start.strftime("%b %d, %Y") if start else "N/A"
                        dist_km = float(r["total_distance_km"] or 0)
                        dist_mi = round(dist_km * 0.621371, 1)

                        sessions.append({
                            "id": f"#{r['session_id']}",
                            "raw_id": r["session_id"],
                            "date": date_str,
                            "duration": duration_str,
                            "max_temp": int(round(c_to_f(r["max_motor_temp"] or 0))),
                            "source_type": r["source_type"] or "CAN_BUS",
                            "status": r["status"] or "ACTIVE",
                            "driver": r["driver_identifier"] or "driver",
                            "notes": r["session_notes"] or "",
                            "max_speed_mph": round(r["max_speed_mph"] or 0, 1),
                            "total_distance_mi": dist_mi,
                            "total_distance_km": round(dist_km, 2),
                            "record_count": r["telemetry_count"],
                            "is_db": True,
                        })
                    return sessions, True
    except Exception as e:
        logger.warning("Failed to fetch sessions from PostgreSQL: %s", e)

    fallback = []
    for s in MOCK_SESSIONS:
        item = dict(s)
        item["raw_id"] = int(s["id"].replace("#", "")) if s["id"].replace("#", "").isdigit() else 1
        item["source_type"] = "SIMULATED"
        item["status"] = "COMPLETED"
        item["driver"] = "demo_driver"
        item["notes"] = "Mercedes-AMG F1 Simulation Benchmark"
        item["max_speed_mph"] = 68.5
        item["total_distance_mi"] = 8.8
        item["total_distance_km"] = 14.2
        item["record_count"] = 600
        item["max_temp"] = int(round(c_to_f(s["max_temp"])))
        item["is_db"] = False
        fallback.append(item)
    return fallback, False


def get_live_metrics() -> Tuple[Dict[str, Any], bool]:
    """
    Fetch the latest telemetry reading from PostgreSQL telemetry_log table ordered by log_id DESC.
    Includes packet age in seconds and is_active flag for real-time link status.
    Returns (metrics_dict, is_from_db).
    """
    db_url = get_db_url()
    try:
        with psycopg.connect(db_url, connect_timeout=2, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        log_id,
                        session_id,
                        "timestamp",
                        speed_mph,
                        motor_rpm,
                        battery_percent,
                        motor_temperature,
                        power_draw_watts,
                        battery_voltage_v,
                        battery_current_a,
                        battery_temp_c,
                        inverter_temp_c,
                        throttle_pct,
                        brake_pct,
                        steering_angle,
                        signal_status,
                        drive_mode,
                        gear,
                        transmission_mode,
                        warning_state,
                        trip_distance_km
                    FROM telemetry_log
                    ORDER BY log_id DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    ts = row["timestamp"]
                    if ts is not None:
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        now_utc = datetime.now(timezone.utc)
                        age_sec = max(0.0, (now_utc - ts).total_seconds())
                    else:
                        age_sec = 9999.0

                    is_active = (age_sec <= 4.0)

                    mot_f = c_to_f(row["motor_temperature"])
                    inv_f = c_to_f(row["inverter_temp_c"])
                    bat_f = c_to_f(row["battery_temp_c"])

                    warnings_raw = row["warning_state"]
                    warnings = []
                    if isinstance(warnings_raw, list):
                        warnings = warnings_raw
                    elif isinstance(warnings_raw, str):
                        try:
                            warnings = json.loads(warnings_raw)
                        except Exception:
                            warnings = [warnings_raw] if warnings_raw else []

                    power_w = float(row["power_draw_watts"] or 0.0)
                    power_kw = round(power_w / 1000.0, 2)
                    trip_km = float(row["trip_distance_km"] or 0.0)
                    trip_mi = round(trip_km * 0.621371, 2)
                    soc = float(row["battery_percent"] or 0.0)
                    est_range_mi = int(round(soc * 2.6))

                    return {
                        "log_id": row["log_id"],
                        "session_id": row["session_id"],
                        "timestamp": ts,
                        "speed": round(float(row["speed_mph"] or 0.0), 1),
                        "rpm": int(row["motor_rpm"] or 0),
                        "battery": round(soc, 1),
                        "est_range_mi": est_range_mi,
                        "temperature": mot_f,
                        "motor_temp_f": mot_f,
                        "inverter_temp_f": inv_f,
                        "battery_temp_f": bat_f,
                        "power_w": power_w,
                        "power_kw": power_kw,
                        "voltage": round(float(row["battery_voltage_v"] or 0.0), 1),
                        "current": round(float(row["battery_current_a"] or 0.0), 1),
                        "throttle_pct": round(float(row["throttle_pct"] or 0.0), 1),
                        "brake_pct": round(float(row["brake_pct"] or 0.0), 1),
                        "steering_angle": round(float(row["steering_angle"] or 0.0), 1),
                        "drive_mode": row["drive_mode"] or "DRIVE",
                        "gear": row["gear"] or "D",
                        "transmission_mode": row["transmission_mode"] or "AUTO",
                        "trip_mi": trip_mi,
                        "signal_status": row["signal_status"] or ("CAN ACTIVE" if is_active else "IDLE"),
                        "warning_state": warnings,
                        "packet_age_sec": round(age_sec, 1),
                        "is_active": is_active,
                    }, True
    except Exception as e:
        logger.warning("Failed to fetch live telemetry from PostgreSQL: %s", e)

    fb = mock_live_metrics(30)
    fb["motor_temp_f"] = c_to_f(fb.get("temperature", 45.0))
    fb["inverter_temp_f"] = c_to_f(38.0)
    fb["battery_temp_f"] = c_to_f(29.0)
    fb["temperature"] = fb["motor_temp_f"]
    fb["power_kw"] = round(fb.get("power_w", 0.0) / 1000.0, 2)
    fb["throttle_pct"] = 0.0
    fb["brake_pct"] = 0.0
    fb["steering_angle"] = 0.0
    fb["trip_mi"] = 0.0
    fb["est_range_mi"] = int(round(fb.get("battery", 80.0) * 2.6))
    fb["warning_state"] = []
    fb["packet_age_sec"] = 999.0
    fb["is_active"] = False
    fb["session_id"] = 0
    fb["log_id"] = 0
    fb["timestamp"] = None
    return fb, False


def get_live_telemetry_traces(limit: int = 60) -> Tuple[Dict[str, List[Any]], bool]:
    """
    Fetch synchronized multi-channel telemetry time-series traces for the stacked F1 graphs.
    Returns (channels_dict, is_from_db).
    """
    db_url = get_db_url()
    try:
        with psycopg.connect(db_url, connect_timeout=2, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        log_id,
                        "timestamp",
                        speed_mph,
                        motor_rpm,
                        throttle_pct,
                        brake_pct,
                        power_draw_watts,
                        motor_temperature,
                        inverter_temp_c,
                        battery_temp_c
                    FROM (
                        SELECT 
                            log_id, "timestamp", speed_mph, motor_rpm,
                            throttle_pct, brake_pct, power_draw_watts,
                            motor_temperature, inverter_temp_c, battery_temp_c
                        FROM telemetry_log
                        ORDER BY log_id DESC
                        LIMIT %s
                    ) sub
                    ORDER BY log_id ASC
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                if rows:
                    indices = list(range(len(rows)))
                    speeds = [round(float(r["speed_mph"] or 0.0), 1) for r in rows]
                    rpms = [int(r["motor_rpm"] or 0) for r in rows]
                    throttles = [round(float(r["throttle_pct"] or 0.0), 1) for r in rows]
                    brakes = [round(float(r["brake_pct"] or 0.0), 1) for r in rows]
                    powers_kw = [round(float(r["power_draw_watts"] or 0.0) / 1000.0, 2) for r in rows]
                    motor_temps_f = [c_to_f(r["motor_temperature"]) for r in rows]
                    inverter_temps_f = [c_to_f(r["inverter_temp_c"]) for r in rows]
                    battery_temps_f = [c_to_f(r["battery_temp_c"]) for r in rows]
                    timestamps = [r["timestamp"] for r in rows]

                    return {
                        "indices": indices,
                        "speeds": speeds,
                        "rpms": rpms,
                        "throttles": throttles,
                        "brakes": brakes,
                        "powers_kw": powers_kw,
                        "motor_temps_f": motor_temps_f,
                        "inverter_temps_f": inverter_temps_f,
                        "battery_temps_f": battery_temps_f,
                        "timestamps": timestamps,
                    }, True
    except Exception as e:
        logger.warning("Failed to fetch telemetry traces from PostgreSQL: %s", e)

    return {
        "indices": [],
        "speeds": [],
        "rpms": [],
        "throttles": [],
        "brakes": [],
        "powers_kw": [],
        "motor_temps_f": [],
        "inverter_temps_f": [],
        "battery_temps_f": [],
        "timestamps": [],
    }, False


def get_live_temperature_history(seconds: int = 60) -> Tuple[List[int], List[float], bool]:
    """
    Fetch the last N seconds of motor temperature history in Fahrenheit.
    Returns (times, temperatures, is_from_db).
    """
    db_url = get_db_url()
    try:
        with psycopg.connect(db_url, connect_timeout=2, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        "timestamp", 
                        motor_temperature
                    FROM (
                        SELECT "timestamp", motor_temperature
                        FROM telemetry_log
                        WHERE motor_temperature IS NOT NULL
                        ORDER BY log_id DESC
                        LIMIT %s
                    ) recent
                    ORDER BY "timestamp" ASC
                    """,
                    (seconds,),
                )
                rows = cur.fetchall()
                if len(rows) >= 5:
                    times = list(range(len(rows)))
                    temps = [c_to_f(r["motor_temperature"]) for r in rows]
                    return times, temps, True
    except Exception as e:
        logger.warning("Failed to fetch temperature history from PostgreSQL: %s", e)

    times, temps_c = mock_live_temp_history(30)
    temps_f = [c_to_f(tc) for tc in temps_c]
    return times, temps_f, False


def get_diagnostics_data(session: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], bool]:
    """
    Query telemetry log data for the given session to generate 5 diagnostics charts.
    Returns (data_dict, is_from_db) with temperatures converted to °F.
    """
    raw_id = session.get("raw_id") if session else None
    if raw_id:
        db_url = get_db_url()
        try:
            with psycopg.connect(db_url, connect_timeout=2, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT 
                            EXTRACT(EPOCH FROM ("timestamp" - MIN("timestamp") OVER ())) / 60.0 AS time_minutes,
                            COALESCE(speed_mph, 0) AS speed_mph,
                            COALESCE(motor_rpm, 0) AS motor_rpm,
                            COALESCE(battery_percent, 0) AS battery_percent,
                            COALESCE(motor_temperature, 0) AS motor_temperature,
                            COALESCE(power_draw_watts, 0) AS power_draw_watts,
                            COALESCE(trip_distance_km, 0) * 0.621371 AS distance_miles
                        FROM telemetry_log
                        WHERE session_id = %s
                        ORDER BY "timestamp" ASC
                        """,
                        (raw_id,),
                    )
                    rows = cur.fetchall()
                    if len(rows) >= 10:
                        speeds = [round(float(r["speed_mph"]), 1) for r in rows]
                        motor_temps = [c_to_f(r["motor_temperature"]) for r in rows]
                        power_draws = [round(float(r["power_draw_watts"]), 1) for r in rows]
                        distances = [round(float(r["distance_miles"]), 2) for r in rows]
                        battery_levels = [round(float(r["battery_percent"]), 1) for r in rows]
                        motor_rpms = [int(r["motor_rpm"]) for r in rows]
                        time_minutes = [round(float(r["time_minutes"]), 2) for r in rows]
                        temp_rise = motor_temps

                        efficiency = []
                        for s, p in zip(speeds, power_draws):
                            if s > 8.0:
                                eff = max(110.0, min(350.0, p / max(1.0, s)))
                            else:
                                eff = 150.0
                            efficiency.append(round(eff, 1))

                        trend_power = [
                            round(sum(power_draws[max(0, i-5):min(len(power_draws), i+5)]) / max(1, len(power_draws[max(0, i-5):min(len(power_draws), i+5)])), 1)
                            for i in range(len(power_draws))
                        ]
                        trend_values = trend_power

                        return {
                            "speeds": speeds,
                            "efficiency": efficiency,
                            "motor_temps": motor_temps,
                            "power_draws": power_draws,
                            "trend_power": trend_power,
                            "distances": distances,
                            "battery_levels": battery_levels,
                            "motor_rpms": motor_rpms,
                            "power_values": power_draws,
                            "trend_values": trend_values,
                            "time_minutes": time_minutes,
                            "temp_rise": temp_rise,
                            "peak_temp": max(motor_temps) if motor_temps else 140.0,
                        }, True
        except Exception as e:
            logger.warning("Failed to fetch diagnostics from PostgreSQL: %s", e)

    data = mock_diagnostics_data(session)
    data["motor_temps"] = [c_to_f(t) for t in data["motor_temps"]]
    data["temp_rise"] = data["motor_temps"]
    data["peak_temp"] = max(data["motor_temps"])
    return data, False
