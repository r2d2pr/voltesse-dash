"""
Voltesse Dash - PostgreSQL Database Module
Handles telemetry logging and vehicle session management with thread-safe batched
asynchronous writes. Follows the logical database design in the SRS (section 3.4):
TECHNICIAN_USER, VEHICLE_SESSION, TELEMETRY_LOG and BACKUP_LOG (see db/schema.sql).

Provides granular write access controls, pre-flight verification, read-only enforcement,
session retention (last N sessions), and session export capabilities (CSV / JSON).

The dashboard must never freeze or crash because the database is unavailable, so every
database failure here is logged and handled instead of being raised to the GUI thread.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import queue
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

logger = logging.getLogger("voltesse.database")

# The connection password is NOT stored here. Set VOLTESSE_DB_URL (or PGPASSWORD / ~/.pgpass).
DEFAULT_DB_URL = "postgresql://voltesse@localhost:5432/voltesse_dash"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

KMH_TO_MPH = 0.621371
# Maximum readings kept in memory while the database is unreachable (oldest dropped first).
MAX_PENDING_ROWS = 5000

# Order must match the %s placeholders in INSERT_TELEMETRY_SQL.
INSERT_TELEMETRY_SQL = """
    INSERT INTO telemetry_log (
        session_id, "timestamp", speed_mph, motor_rpm, battery_percent,
        motor_temperature, power_draw_watts, signal_status, warning_state,
        battery_voltage_v, battery_current_a, battery_temp_c, inverter_temp_c,
        throttle_pct, brake_pct, drive_mode, trip_distance_km, steering_angle,
        gear, transmission_mode
    ) VALUES (
        %s, to_timestamp(%s::double precision), %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s
    )
"""


@dataclass
class TelemetryRecord:
    """One snapshot from a telemetry source. Units are the app's native ones (km/h, kW)."""

    timestamp: float  # seconds since the Unix epoch
    speed_kmh: float
    motor_rpm: int
    battery_soc: float
    battery_voltage: float
    battery_current: float
    battery_power_kw: float
    battery_temp_c: float
    motor_temp_c: float
    inverter_temp_c: float
    throttle_pct: float
    brake_pct: float
    drive_mode: str
    trip_distance_km: float
    warnings: List[str]
    steering_angle: float = 0.0
    gear: str = "D"
    transmission_mode: str = "AUTO"

    def to_row(self, session_id: int, signal_status: Optional[str] = None) -> Tuple:
        """Maps the record to TELEMETRY_LOG columns (speed -> mph, power kW -> watts)."""
        return (
            session_id,
            self.timestamp,
            max(0.0, self.speed_kmh * KMH_TO_MPH),
            max(0, int(self.motor_rpm)),
            min(100.0, max(0.0, self.battery_soc)),
            self.motor_temp_c,
            self.battery_power_kw * 1000.0,
            signal_status,
            Jsonb(list(self.warnings)),
            self.battery_voltage,
            self.battery_current,
            self.battery_temp_c,
            self.inverter_temp_c,
            self.throttle_pct,
            self.brake_pct,
            self.drive_mode,
            self.trip_distance_km,
            self.steering_angle,
            self.gear,
            self.transmission_mode,
        )


def redact_db_url(url: str) -> str:
    """Hides the password in a connection URL so it is safe to log."""
    return re.sub(r"(://[^:/@]+):[^@]*@", r"\1:***@", url)


def _csv_cell(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class DatabaseManager:
    """
    Manages PostgreSQL storage for telemetry and vehicle sessions.
    Runs an asynchronous background worker thread with batched commits so database I/O
    never blocks the GUI thread. Includes granular write access controls, pre-flight
    connection checks, read-only enforcement, retention, and session export.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        batch_size: int = 25,
        flush_interval_sec: float = 1.0,
        write_enabled: bool = True,
        read_only: bool = False,
        export_dir: str = "data/exports",
        connect_timeout_sec: int = 3,
    ):
        self.db_url = db_url or os.environ.get("VOLTESSE_DB_URL") or DEFAULT_DB_URL
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self.read_only = read_only
        self.write_enabled = (not read_only) and write_enabled
        self.export_dir = Path(export_dir)
        self.connect_timeout_sec = connect_timeout_sec

        # Internal verification flags
        self._write_verified = False
        self._write_error_reason: Optional[str] = None
        self._schema_ready = False

        self._queue: queue.Queue = queue.Queue(maxsize=10000)
        self._stop_event = threading.Event()
        self._current_session_id: Optional[int] = None
        self._session_source: Optional[str] = None
        self._source_type = "CAN_BUS"
        self._signal_status: Optional[str] = None
        self._writer_thread: Optional[threading.Thread] = None
        self._session_retry_at = 0.0

        if self.read_only:
            logger.info("DatabaseManager initialized in strict READ-ONLY mode for: %s", redact_db_url(self.db_url))
            self._verify_read_access()
        else:
            self._prepare_for_writing()

    # -----------------------------------------------------------------
    # Connections and verification
    # -----------------------------------------------------------------

    def _get_connection(self, read_only: Optional[bool] = None) -> psycopg.Connection:
        """Opens a new connection. Rows come back as dicts. Caller commits/closes (use `with`)."""
        use_ro = self.read_only if read_only is None else read_only
        conn = psycopg.connect(
            self.db_url,
            row_factory=dict_row,
            connect_timeout=self.connect_timeout_sec,
        )
        if use_ro:
            # The server rejects any write on this connection.
            conn.read_only = True
        return conn

    def _verify_read_access(self) -> bool:
        """Verifies that the database is reachable for reading."""
        try:
            with self._get_connection(read_only=True) as conn:
                conn.execute("SELECT 1")
            return True
        except psycopg.Error as e:
            logger.warning("Read-only verification failed for %s: %s", redact_db_url(self.db_url), e)
            return False

    def verify_write_access(self) -> bool:
        """Pre-flight test: can we connect to PostgreSQL and run a statement?"""
        if self.read_only:
            self._write_verified = False
            self._write_error_reason = "Database opened in strict read-only mode."
            return False

        try:
            with self._get_connection(read_only=False) as conn:
                conn.execute("SELECT 1")
            self._write_verified = True
            self._write_error_reason = None
            return True
        except psycopg.Error as e:
            self._write_verified = False
            self._write_error_reason = str(e).strip()
            logger.warning("Database write access verification failed: %s", self._write_error_reason)
            return False

    def _prepare_for_writing(self) -> bool:
        """Verifies the connection, creates the schema if needed, and starts the writer thread."""
        if not self.verify_write_access():
            return False
        if not self._schema_ready:
            self._init_database()
        if self._schema_ready:
            self._start_writer()
        return self._schema_ready

    def is_write_enabled(self) -> bool:
        """Returns True if database write logging is currently active."""
        return self.write_enabled and not self.read_only and self._write_verified and self._schema_ready

    def set_write_access(self, enabled: bool) -> bool:
        """
        Dynamically enables or disables write access to the database at runtime.
        Returns the resulting effective write state.
        """
        if self.read_only:
            logger.warning("Cannot enable write access: Database is in strict READ-ONLY mode.")
            return False

        if enabled:
            if not (self._write_verified and self._schema_ready):
                # Database may have come back since startup: try again.
                if not self._prepare_for_writing():
                    logger.warning("Cannot enable write access: %s", self._write_error_reason)
                    return False
            self.write_enabled = True
        else:
            self.write_enabled = False

        logger.info("Database write access %s", "ENABLED" if self.write_enabled else "DISABLED")
        return self.is_write_enabled() if enabled else False

    # -----------------------------------------------------------------
    # Schema
    # -----------------------------------------------------------------

    def _init_database(self) -> None:
        """Creates the SRS tables, indexes, views and retention function if they do not exist."""
        if self.read_only:
            return
        try:
            schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
            with self._get_connection(read_only=False) as conn:
                conn.execute(schema_sql)
            self._schema_ready = True
            logger.info("PostgreSQL schema ready at %s", redact_db_url(self.db_url))
        except (OSError, psycopg.Error) as e:
            self._schema_ready = False
            self._write_error_reason = str(e).strip()
            logger.error("Could not initialize database schema: %s", self._write_error_reason)

    # -----------------------------------------------------------------
    # Sessions (VEHICLE_SESSION)
    # -----------------------------------------------------------------

    def set_source_type(self, source_type: str) -> None:
        """
        Tells the manager which telemetry source is active (CAN_BUS, SIMULATION, TEST).
        If the source changes during a running session, that session is marked MIXED.
        """
        self._source_type = source_type
        if (
            self._current_session_id is not None
            and self._session_source not in (None, source_type, "MIXED")
            and self.is_write_enabled()
        ):
            try:
                with self._get_connection(read_only=False) as conn:
                    conn.execute(
                        "UPDATE vehicle_session SET source_type = 'MIXED' WHERE session_id = %s",
                        (self._current_session_id,),
                    )
                self._session_source = "MIXED"
            except psycopg.Error as e:
                logger.warning("Could not mark session as MIXED: %s", e)

    def set_signal_status(self, status: str) -> None:
        """Latest connection status from the active telemetry source (stored with each reading)."""
        self._signal_status = status

    def start_session(
        self,
        initial_soc: float = 100.0,
        source_type: Optional[str] = None,
        driver_identifier: Optional[str] = None,
    ) -> Optional[int]:
        """Creates a new vehicle session. Returns session_id or None if writes are disabled/unavailable."""
        if not self.is_write_enabled():
            logger.info("Skipping start_session: Database write access is disabled.")
            return None

        source = source_type or self._source_type
        try:
            with self._get_connection(read_only=False) as conn:
                # A session left ACTIVE by a crash or power loss was interrupted (PR-6).
                conn.execute(
                    """
                    UPDATE vehicle_session s
                    SET status = 'INTERRUPTED',
                        end_timestamp = COALESCE(
                            (SELECT max(t."timestamp") FROM telemetry_log t WHERE t.session_id = s.session_id),
                            s.start_timestamp)
                    WHERE s.status = 'ACTIVE'
                    """
                )
                row = conn.execute(
                    """
                    INSERT INTO vehicle_session (source_type, driver_identifier, start_soc_percent, status)
                    VALUES (%s, %s, %s, 'ACTIVE')
                    RETURNING session_id
                    """,
                    (source, driver_identifier, initial_soc),
                ).fetchone()
            self._current_session_id = row["session_id"]
            self._session_source = source
            logger.info("Started vehicle session ID: %d (%s)", self._current_session_id, source)
            return self._current_session_id
        except psycopg.Error as e:
            logger.error("Could not start session: %s", e)
            return None

    def end_session(
        self,
        final_soc: float,
        max_speed: float,
        avg_speed: float,
        distance_km: float,
        energy_kwh: float,
    ) -> None:
        """Closes the current session. Speeds are passed in km/h and stored as mph."""
        if self._current_session_id is None or not self.is_write_enabled():
            return

        session_id = self._current_session_id
        try:
            with self._get_connection(read_only=False) as conn:
                conn.execute(
                    """
                    UPDATE vehicle_session
                    SET end_timestamp = now(),
                        end_soc_percent = %s,
                        max_speed_mph = %s,
                        avg_speed_mph = %s,
                        total_distance_km = %s,
                        total_energy_kwh = %s,
                        status = 'COMPLETED'
                    WHERE session_id = %s
                    """,
                    (
                        final_soc,
                        max_speed * KMH_TO_MPH,
                        avg_speed * KMH_TO_MPH,
                        distance_km,
                        energy_kwh,
                        session_id,
                    ),
                )
            logger.info("Ended vehicle session ID: %d", session_id)
            self._current_session_id = None
            self._session_source = None
        except psycopg.Error as e:
            logger.error("Could not end session %d: %s", session_id, e)

    def prune_old_sessions(self, keep_sessions: int = 20, keep_days: int = 0) -> int:
        """
        Session-based retention (SRS PR-4): deletes sessions that are outside the newest
        `keep_sessions` AND older than `keep_days`. Active sessions are never deleted.
        Returns the number of sessions deleted (their telemetry goes with them).
        """
        if self.read_only or not self.is_write_enabled():
            return 0
        try:
            with self._get_connection(read_only=False) as conn:
                row = conn.execute(
                    "SELECT prune_old_sessions(%s, %s) AS deleted", (keep_sessions, keep_days)
                ).fetchone()
            deleted = int(row["deleted"])
            if deleted:
                logger.info("Retention removed %d old session(s).", deleted)
            return deleted
        except psycopg.Error as e:
            logger.error("Retention pruning failed: %s", e)
            return 0

    # -----------------------------------------------------------------
    # Telemetry writing (TELEMETRY_LOG)
    # -----------------------------------------------------------------

    def log_telemetry(self, record: TelemetryRecord) -> bool:
        """
        Enqueues a telemetry record for asynchronous batched persistence.
        Every reading must belong to a session (SRS), so one is started if none is active.
        Returns True if queued, False if write access is disabled/unavailable or the queue is full.
        """
        if not self.is_write_enabled():
            return False

        if self._current_session_id is None:
            # Do not retry on every reading if the database is down (this runs on the GUI thread).
            if time.time() < self._session_retry_at:
                return False
            if self.start_session(initial_soc=record.battery_soc) is None:
                self._session_retry_at = time.time() + 5.0
                return False

        try:
            self._queue.put_nowait((record, self._current_session_id, self._signal_status))
            return True
        except queue.Full:
            logger.warning("Telemetry log queue full, dropping record to protect main thread.")
            return False

    def _start_writer(self) -> None:
        if self.read_only:
            return
        if self._writer_thread is not None and self._writer_thread.is_alive():
            return
        self._stop_event.clear()
        self._writer_thread = threading.Thread(
            target=self._worker_loop,
            name="VoltesseDBWriter",
            daemon=True,
        )
        self._writer_thread.start()

    def _insert_rows_one_by_one(self, conn: psycopg.Connection, batch: List[Tuple]) -> None:
        """Fallback when a batch holds an invalid row: save the good rows, skip and log the bad ones."""
        for row in batch:
            try:
                with conn.cursor() as cur:
                    cur.execute(INSERT_TELEMETRY_SQL, row)
                conn.commit()
            except (psycopg.errors.IntegrityError, psycopg.errors.DataError) as row_error:
                conn.rollback()
                logger.error("Skipping invalid telemetry reading: %s", str(row_error).strip())

    def _flush_batch(self, conn: Optional[psycopg.Connection], batch: List[Tuple]) -> Optional[psycopg.Connection]:
        """
        Writes the batch in one transaction. On success the batch is cleared.
        A bad row (constraint/data error) is isolated and skipped so it cannot block logging.
        Any other failure (for example the database is down) keeps the batch, bounded, for the
        next attempt and drops the connection so a fresh one is opened, which also recovers
        from a database restart.
        """
        try:
            if conn is None or conn.closed:
                conn = self._get_connection(read_only=False)
            try:
                with conn.cursor() as cur:
                    cur.executemany(INSERT_TELEMETRY_SQL, batch)
                conn.commit()
            except (psycopg.errors.IntegrityError, psycopg.errors.DataError) as e:
                logger.error("Invalid reading in batch, saving rows one by one: %s", str(e).strip())
                conn.rollback()
                self._insert_rows_one_by_one(conn, batch)
            batch.clear()
            return conn
        except Exception as e:  # noqa: BLE001 - the writer thread must survive any failure
            logger.error("Error writing telemetry batch (will retry): %s", e)
            try:
                if conn is not None:
                    conn.close()
            except Exception:  # noqa: BLE001
                pass
            if len(batch) > MAX_PENDING_ROWS:
                dropped = len(batch) - MAX_PENDING_ROWS
                del batch[:dropped]
                logger.warning("Dropped %d oldest unsaved readings (database unavailable).", dropped)
            return None

    def _worker_loop(self) -> None:
        """Background thread loop that drains the queue and writes in batches."""
        conn: Optional[psycopg.Connection] = None
        batch: List[Tuple] = []
        last_flush_time = time.time()
        retry_not_before = 0.0

        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                record, session_id, signal_status = self._queue.get(timeout=0.2)
                batch.append(record.to_row(session_id, signal_status))
                self._queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:  # noqa: BLE001
                logger.error("Error preparing telemetry row: %s", e, exc_info=True)
                self._queue.task_done()

            now = time.time()
            should_flush = batch and now >= retry_not_before and (
                len(batch) >= self.batch_size
                or (now - last_flush_time) >= self.flush_interval_sec
                or self._stop_event.is_set()
            )
            if should_flush:
                conn = self._flush_batch(conn, batch)
                last_flush_time = now
                if conn is None:
                    retry_not_before = now + 1.0  # avoid hammering a database that is down

        # Final flush on exit
        if batch:
            conn = self._flush_batch(conn, batch)
            if batch:
                logger.error("Lost %d unsaved readings at shutdown (database unavailable).", len(batch))

        try:
            if conn is not None:
                conn.close()
        except Exception:  # noqa: BLE001
            pass
        logger.info("Database writer thread stopped cleanly.")

    # -----------------------------------------------------------------
    # Queries
    # -----------------------------------------------------------------

    def get_recent_telemetry(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves the most recent telemetry entries for analysis or diagnostics."""
        with self._get_connection(read_only=True) as conn:
            return conn.execute(
                'SELECT * FROM telemetry_log ORDER BY "timestamp" DESC LIMIT %s', (limit,)
            ).fetchall()

    def get_recent_window(self, session_id: Optional[int] = None, seconds: int = 15) -> List[Dict[str, Any]]:
        """
        Telemetry from the last `seconds` of a session, oldest first (SRS PR-7: at least 15 s).
        Measured back from the session's newest reading, so it works for live and finished sessions.
        """
        target_id = session_id or self._current_session_id
        if target_id is None:
            return []
        with self._get_connection(read_only=True) as conn:
            return conn.execute(
                """
                SELECT * FROM telemetry_log
                WHERE session_id = %(sid)s
                  AND "timestamp" >= (SELECT max("timestamp") FROM telemetry_log WHERE session_id = %(sid)s)
                                     - make_interval(secs => %(secs)s)
                ORDER BY "timestamp" ASC
                """,
                {"sid": target_id, "secs": seconds},
            ).fetchall()

    def get_trip_summary(self, session_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Calculates summary statistics for the current or specified session from logged data."""
        target_id = session_id or self._current_session_id
        if target_id is None:
            return None

        with self._get_connection(read_only=True) as conn:
            return conn.execute(
                """
                SELECT
                    COUNT(*) AS sample_count,
                    MIN("timestamp") AS start_time,
                    MAX("timestamp") AS end_time,
                    MAX(speed_mph) AS max_speed_mph,
                    AVG(speed_mph) AS avg_speed_mph,
                    MAX(trip_distance_km) - MIN(trip_distance_km) AS distance_km,
                    MAX(battery_temp_c) AS max_battery_temp_c,
                    MAX(motor_temperature) AS max_motor_temp_c
                FROM telemetry_log
                WHERE session_id = %s
                """,
                (target_id,),
            ).fetchone()

    def get_all_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves vehicle sessions, newest first."""
        with self._get_connection(read_only=True) as conn:
            return conn.execute(
                "SELECT * FROM vehicle_session ORDER BY session_id DESC LIMIT %s", (limit,)
            ).fetchall()

    # -----------------------------------------------------------------
    # Data Export and Dump Capabilities
    # -----------------------------------------------------------------

    def _export_path(self, output_path: Optional[str], stem: str, extension: str) -> str:
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            return output_path
        self.export_dir.mkdir(parents=True, exist_ok=True)
        return str(self.export_dir / f"{stem}_{int(time.time())}.{extension}")

    def export_session_to_csv(self, session_id: int, output_path: Optional[str] = None) -> str:
        """Exports all telemetry rows for a session to CSV. Returns the output file path."""
        with self._get_connection(read_only=True) as conn:
            cur = conn.execute(
                'SELECT * FROM telemetry_log WHERE session_id = %s ORDER BY "timestamp" ASC',
                (session_id,),
            )
            rows = cur.fetchall()
            columns = [col.name for col in cur.description] if cur.description else []

        if not rows:
            raise ValueError(f"No telemetry logs found for session ID {session_id}")

        output_path = self._export_path(output_path, f"session_{session_id}", "csv")
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([_csv_cell(row[c]) for c in columns])

        logger.info("Exported session %d (%d rows) to %s", session_id, len(rows), output_path)
        return output_path

    def export_session_to_json(
        self,
        session_id: int,
        output_path: Optional[str] = None,
        indent: int = 2,
    ) -> str:
        """Exports session metadata and its telemetry to structured JSON. Returns the file path."""
        with self._get_connection(read_only=True) as conn:
            session_meta = conn.execute(
                "SELECT * FROM vehicle_session WHERE session_id = %s", (session_id,)
            ).fetchone() or {"session_id": session_id}
            logs = conn.execute(
                'SELECT * FROM telemetry_log WHERE session_id = %s ORDER BY "timestamp" ASC',
                (session_id,),
            ).fetchall()

        export_data = {
            "session": session_meta,
            "record_count": len(logs),
            "telemetry": logs,
        }
        output_path = self._export_path(output_path, f"session_{session_id}", "json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=indent, default=_json_default)

        logger.info("Exported session %d JSON to %s", session_id, output_path)
        return output_path

    def export_all_sessions_summary_csv(self, output_path: Optional[str] = None) -> str:
        """Exports a summary of all vehicle sessions to CSV. Returns the output file path."""
        with self._get_connection(read_only=True) as conn:
            cur = conn.execute("SELECT * FROM vehicle_session ORDER BY session_id ASC")
            rows = cur.fetchall()
            columns = [col.name for col in cur.description] if cur.description else []

        output_path = self._export_path(output_path, "all_sessions", "csv")
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([_csv_cell(row[c]) for c in columns])

        logger.info("Exported %d sessions to %s", len(rows), output_path)
        return output_path

    def close(self) -> None:
        """Signals the writer thread to finish and flushes remaining records."""
        self._stop_event.set()
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=5.0)
        logger.info("Database manager closed.")
