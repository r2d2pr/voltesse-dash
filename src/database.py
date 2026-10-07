"""
Voltesse Dash - SQLite Database Module
Handles telemetry logging and trip session management with thread-safe batched asynchronous writes.
Provides granular write access controls, pre-flight verification, read-only enforcement,
and session export capabilities (CSV / JSON).
"""

import csv
from dataclasses import dataclass, asdict
import json
import logging
import os
from pathlib import Path
import queue
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("voltesse.database")


@dataclass
class TelemetryRecord:
    timestamp: float
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

    def to_row(self, session_id: Optional[int] = None) -> Tuple:
        warnings_json = json.dumps(self.warnings)
        return (
            self.timestamp,
            session_id,
            self.speed_kmh,
            self.motor_rpm,
            self.battery_soc,
            self.battery_voltage,
            self.battery_current,
            self.battery_power_kw,
            self.battery_temp_c,
            self.motor_temp_c,
            self.inverter_temp_c,
            self.throttle_pct,
            self.brake_pct,
            self.drive_mode,
            self.trip_distance_km,
            warnings_json,
            self.steering_angle,
            self.gear,
            self.transmission_mode,
        )


class DatabaseManager:
    """
    Manages SQLite database storage for telemetry and trip logs.
    Runs an asynchronous background worker thread with batched commits to prevent
    I/O bottlenecks on embedded systems like the Raspberry Pi.
    Includes granular write access controls, pre-flight permission checks,
    read-only enforcement, and session export capabilities.
    """

    def __init__(
        self,
        db_path: str = "data/voltesse_telemetry.db",
        batch_size: int = 25,
        flush_interval_sec: float = 1.0,
        write_enabled: bool = True,
        read_only: bool = False,
    ):
        self.db_path = Path(db_path)
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self.read_only = read_only
        self.write_enabled = (not read_only) and write_enabled

        # Internal verification flags
        self._write_verified = False
        self._write_error_reason: Optional[str] = None

        self._queue: queue.Queue = queue.Queue(maxsize=10000)
        self._stop_event = threading.Event()
        self._current_session_id: Optional[int] = None
        self._writer_thread: Optional[threading.Thread] = None

        if not self.read_only:
            # Ensure target directory exists and verify write permissions
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.verify_write_access()
            # Initialize tables on caller thread
            self._init_database()
            # Start writer worker thread if write logging is enabled
            self._start_writer()
        else:
            logger.info("DatabaseManager initialized in strict READ-ONLY mode for: %s", self.db_path)
            # If database exists, verify readability
            if self.db_path.exists():
                self._verify_read_access()

    def _get_connection(self, read_only: Optional[bool] = None) -> sqlite3.Connection:
        use_ro = self.read_only if read_only is None else read_only
        if use_ro and self.db_path.exists():
            # Open using SQLite URI read-only flag
            uri_path = f"file:{self.db_path.resolve().as_posix()}?mode=ro"
            conn = sqlite3.connect(
                uri_path,
                uri=True,
                timeout=30.0,
                check_same_thread=False,
            )
        else:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
            )

        conn.row_factory = sqlite3.Row
        if not use_ro:
            # Configure WAL mode and synchronous settings optimized for embedded SD card / flash storage
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA temp_store = MEMORY;")
            conn.execute("PRAGMA cache_size = -8000;")  # 8MB memory cache
        return conn

    def _verify_read_access(self) -> bool:
        """Verifies that the database is readable in read-only mode."""
        try:
            conn = self._get_connection(read_only=True)
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1;")
            conn.close()
            return True
        except Exception as e:
            logger.warning("Read-only verification failed for %s: %s", self.db_path, e)
            return False

    def verify_write_access(self) -> bool:
        """
        Pre-flight test verifying whether write operations can be performed
        on the SQLite file and destination directory.
        """
        if self.read_only:
            self._write_verified = False
            self._write_error_reason = "Database opened in strict read-only mode."
            return False

        try:
            parent_dir = self.db_path.parent
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)

            # Test directory write permission by writing a micro temp file
            test_file = parent_dir / f".write_test_{os.getpid()}_{int(time.time() * 1000)}.tmp"
            with open(test_file, "w") as f:
                f.write("ok")
            test_file.unlink(missing_ok=True)

            # Test database file writability if it already exists
            if self.db_path.exists() and not os.access(self.db_path, os.W_OK):
                self._write_verified = False
                self._write_error_reason = f"Database file {self.db_path} is write-protected."
                logger.warning(self._write_error_reason)
                return False

            self._write_verified = True
            self._write_error_reason = None
            return True
        except Exception as e:
            self._write_verified = False
            self._write_error_reason = str(e)
            logger.warning("Database write access verification failed: %s", e)
            return False

    def is_write_enabled(self) -> bool:
        """Returns True if database write logging is currently active."""
        return self.write_enabled and not self.read_only and self._write_verified

    def set_write_access(self, enabled: bool) -> bool:
        """
        Dynamically enables or disables write access to the database at runtime.
        Returns the resulting effective write state.
        """
        if self.read_only:
            logger.warning("Cannot enable write access: Database is in strict READ-ONLY mode.")
            return False

        if enabled:
            if not self._write_verified:
                if not self.verify_write_access():
                    logger.warning("Cannot enable write access: %s", self._write_error_reason)
                    return False
            self.write_enabled = True
        else:
            self.write_enabled = False

        logger.info("Database write access %s", "ENABLED" if self.write_enabled else "DISABLED")
        return self.write_enabled

    def _init_database(self) -> None:
        """Create tables and indexes if they do not exist."""
        if self.read_only:
            return

        conn = self._get_connection(read_only=False)
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trip_sessions (\n                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        start_time REAL NOT NULL,
                        end_time REAL,
                        start_soc REAL,
                        end_soc REAL,
                        max_speed_kmh REAL DEFAULT 0.0,
                        avg_speed_kmh REAL DEFAULT 0.0,
                        total_distance_km REAL DEFAULT 0.0,
                        total_energy_kwh REAL DEFAULT 0.0,
                        status TEXT DEFAULT 'ACTIVE'
                    );
                    """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS telemetry_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        session_id INTEGER,
                        speed_kmh REAL NOT NULL,
                        motor_rpm INTEGER NOT NULL,
                        battery_soc REAL NOT NULL,
                        battery_voltage REAL NOT NULL,
                        battery_current REAL NOT NULL,
                        battery_power_kw REAL NOT NULL,
                        battery_temp_c REAL NOT NULL,
                        motor_temp_c REAL NOT NULL,
                        inverter_temp_c REAL NOT NULL,
                        throttle_pct REAL NOT NULL,
                        brake_pct REAL NOT NULL,
                        drive_mode TEXT NOT NULL,
                        trip_distance_km REAL NOT NULL,
                        warnings TEXT,
                        steering_angle REAL DEFAULT 0.0,
                        gear TEXT DEFAULT 'D',
                        transmission_mode TEXT DEFAULT 'AUTO',
                        FOREIGN KEY(session_id) REFERENCES trip_sessions(session_id) ON DELETE SET NULL
                    );
                    """
                )

                # Migration checks for existing databases
                for col_name, col_type in [
                    ("steering_angle", "REAL DEFAULT 0.0"),
                    ("gear", "TEXT DEFAULT 'D'"),
                    ("transmission_mode", "TEXT DEFAULT 'AUTO'"),
                ]:
                    try:
                        conn.execute(f"ALTER TABLE telemetry_logs ADD COLUMN {col_name} {col_type};")
                    except sqlite3.OperationalError:
                        pass

                # Indexes for fast querying and time-range filtering
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_logs (timestamp);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_telemetry_session ON telemetry_logs (session_id);"
                )
            logger.info("SQLite schema initialized successfully at %s", self.db_path)
        finally:
            conn.close()

    def start_session(self, initial_soc: float = 100.0) -> Optional[int]:
        """Creates a new trip session. Returns session_id or None if writes disabled."""
        if not self.is_write_enabled():
            logger.info("Skipping start_session: Database write access is disabled.")
            return None

        conn = self._get_connection(read_only=False)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO trip_sessions (start_time, start_soc, status)
                    VALUES (?, ?, 'ACTIVE')
                    """,
                    (time.time(), initial_soc),
                )
                self._current_session_id = cursor.lastrowid
                logger.info("Started new trip session ID: %d", self._current_session_id)
                return self._current_session_id
        finally:
            conn.close()

    def end_session(
        self,
        final_soc: float,
        max_speed: float,
        avg_speed: float,
        distance_km: float,
        energy_kwh: float,
    ) -> None:
        """Closes the current trip session with summary statistics."""
        if self._current_session_id is None or not self.is_write_enabled():
            return

        conn = self._get_connection(read_only=False)
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE trip_sessions
                    SET end_time = ?,
                        end_soc = ?,
                        max_speed_kmh = ?,
                        avg_speed_kmh = ?,
                        total_distance_km = ?,
                        total_energy_kwh = ?,
                        status = 'COMPLETED'
                    WHERE session_id = ?
                    """,
                    (
                        time.time(),
                        final_soc,
                        max_speed,
                        avg_speed,
                        distance_km,
                        energy_kwh,
                        self._current_session_id,
                    ),
                )
                logger.info("Ended trip session ID: %d", self._current_session_id)
                self._current_session_id = None
        finally:
            conn.close()

    def log_telemetry(self, record: TelemetryRecord) -> bool:
        """
        Enqueues a telemetry record for asynchronous batched persistence.
        Returns True if queued, False if write access is disabled or queue is full.
        """
        if not self.is_write_enabled():
            return False

        try:
            self._queue.put_nowait((record, self._current_session_id))
            return True
        except queue.Full:
            logger.warning("Telemetry log queue full, dropping record to protect main thread.")
            return False

    def _start_writer(self) -> None:
        if self.read_only:
            return
        self._stop_event.clear()
        self._writer_thread = threading.Thread(
            target=self._worker_loop,
            name="VoltesseDBWriter",
            daemon=True,
        )
        self._writer_thread.start()

    def _worker_loop(self) -> None:
        """Background thread loop that drains the queue and writes in batches."""
        conn = self._get_connection(read_only=False)
        batch: List[Tuple] = []
        last_flush_time = time.time()

        insert_sql = """
            INSERT INTO telemetry_logs (
                timestamp, session_id, speed_kmh, motor_rpm, battery_soc,
                battery_voltage, battery_current, battery_power_kw, battery_temp_c,
                motor_temp_c, inverter_temp_c, throttle_pct, brake_pct,
                drive_mode, trip_distance_km, warnings, steering_angle, gear, transmission_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                try:
                    record, session_id = self._queue.get(timeout=0.2)
                    batch.append(record.to_row(session_id))
                    self._queue.task_done()
                except queue.Empty:
                    pass

                now = time.time()
                should_flush = (
                    len(batch) >= self.batch_size
                    or (batch and (now - last_flush_time) >= self.flush_interval_sec)
                    or (self._stop_event.is_set() and batch)
                )

                if should_flush:
                    with conn:
                        conn.executemany(insert_sql, batch)
                    batch.clear()
                    last_flush_time = now

            except Exception as e:
                logger.error("Error in database writer worker: %s", e, exc_info=True)

        # Final flush on exit
        if batch:
            try:
                with conn:
                    conn.executemany(insert_sql, batch)
                batch.clear()
            except Exception as e:
                logger.error("Error during final database flush: %s", e)

        conn.close()
        logger.info("Database writer thread stopped cleanly.")

    def get_recent_telemetry(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves recent telemetry entries for analysis or diagnostics."""
        conn = self._get_connection(read_only=True)
        try:
            cursor = conn.execute(
                """
                SELECT * FROM telemetry_logs
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_trip_summary(self, session_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Calculates current or specified session summary statistics from logged data."""
        target_id = session_id or self._current_session_id
        if target_id is None:
            return None

        conn = self._get_connection(read_only=True)
        try:
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as sample_count,
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time,
                    MAX(speed_kmh) as max_speed,
                    AVG(speed_kmh) as avg_speed,
                    MAX(trip_distance_km) - MIN(trip_distance_km) as distance_km,
                    MAX(battery_temp_c) as max_battery_temp,
                    MAX(motor_temp_c) as max_motor_temp
                FROM telemetry_logs
                WHERE session_id = ?
                """,
                (target_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves all trip sessions."""
        conn = self._get_connection(read_only=True)
        try:
            cursor = conn.execute(
                """
                SELECT * FROM trip_sessions
                ORDER BY session_id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    # -----------------------------------------------------------------
    # Data Export and Dump Capabilities
    # -----------------------------------------------------------------

    def export_session_to_csv(self, session_id: int, output_path: Optional[str] = None) -> str:
        """
        Exports all telemetry rows for a given trip session to a CSV file.
        Returns the output file path.
        """
        conn = self._get_connection(read_only=True)
        try:
            cursor = conn.execute(
                """
                SELECT * FROM telemetry_logs
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                raise ValueError(f"No telemetry logs found for session ID {session_id}")

            columns = [desc[0] for desc in cursor.description]

            if not output_path:
                export_dir = self.db_path.parent / "exports"
                export_dir.mkdir(parents=True, exist_ok=True)
                output_path = str(export_dir / f"session_{session_id}_{int(time.time())}.csv")
            else:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(list(row))

            logger.info("Exported session %d (%d rows) to %s", session_id, len(rows), output_path)
            return output_path
        finally:
            conn.close()

    def export_session_to_json(
        self,
        session_id: int,
        output_path: Optional[str] = None,
        indent: int = 2,
    ) -> str:
        """
        Exports trip session metadata and its telemetry logs to a structured JSON file.
        Returns the output file path.
        """
        conn = self._get_connection(read_only=True)
        try:
            # Session metadata
            cur_sess = conn.execute(
                "SELECT * FROM trip_sessions WHERE session_id = ?",
                (session_id,),
            )
            sess_row = cur_sess.fetchone()
            session_meta = dict(sess_row) if sess_row else {"session_id": session_id}

            # Telemetry records
            cur_logs = conn.execute(
                """
                SELECT * FROM telemetry_logs
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,),
            )
            logs = []
            for r in cur_logs.fetchall():
                d = dict(r)
                if "warnings" in d and isinstance(d["warnings"], str):
                    try:
                        d["warnings"] = json.loads(d["warnings"])
                    except Exception:
                        pass
                logs.append(d)

            export_data = {
                "session": session_meta,
                "record_count": len(logs),
                "telemetry": logs,
            }

            if not output_path:
                export_dir = self.db_path.parent / "exports"
                export_dir.mkdir(parents=True, exist_ok=True)
                output_path = str(export_dir / f"session_{session_id}_{int(time.time())}.json")
            else:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=indent)

            logger.info("Exported session %d JSON to %s", session_id, output_path)
            return output_path
        finally:
            conn.close()

    def export_all_sessions_summary_csv(self, output_path: Optional[str] = None) -> str:
        """
        Exports a summary of all trip sessions to a CSV file.
        Returns the output file path.
        """
        conn = self._get_connection(read_only=True)
        try:
            cursor = conn.execute("SELECT * FROM trip_sessions ORDER BY session_id ASC")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            if not output_path:
                export_dir = self.db_path.parent / "exports"
                export_dir.mkdir(parents=True, exist_ok=True)
                output_path = str(export_dir / f"all_sessions_{int(time.time())}.csv")
            else:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(list(row))

            logger.info("Exported %d sessions to %s", len(rows), output_path)
            return output_path
        finally:
            conn.close()

    def close(self) -> None:
        """Signals writer thread to finish and flushes remaining records."""
        self._stop_event.set()
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=3.0)
        logger.info("Database manager closed.")
