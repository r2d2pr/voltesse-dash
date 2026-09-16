"""
Voltesse Dash - SQLite Database Module
Handles telemetry logging and trip session management with thread-safe batched asynchronous writes.
"""

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
        )


class DatabaseManager:
    """
    Manages SQLite database storage for telemetry and trip logs.
    Runs an asynchronous background worker thread with batched commits to prevent
    I/O bottlenecks on embedded systems like the Raspberry Pi.
    """

    def __init__(
        self,
        db_path: str = "data/voltesse_telemetry.db",
        batch_size: int = 25,
        flush_interval_sec: float = 1.0,
    ):
        self.db_path = Path(db_path)
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._queue: queue.Queue = queue.Queue(maxsize=10000)
        self._stop_event = threading.Event()
        self._current_session_id: Optional[int] = None
        self._writer_thread: Optional[threading.Thread] = None

        # Initialize tables on caller thread
        self._init_database()

        # Start writer worker thread
        self._start_writer()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        # Configure WAL mode and synchronous settings optimized for embedded SD card / flash storage
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA cache_size = -8000;")  # 8MB memory cache
        return conn

    def _init_database(self) -> None:
        """Create tables and indexes if they do not exist."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trip_sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                        FOREIGN KEY(session_id) REFERENCES trip_sessions(session_id) ON DELETE SET NULL
                    );
                    """
                )

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

    def start_session(self, initial_soc: float = 100.0) -> int:
        """Creates a new trip session."""
        conn = self._get_connection()
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
        if self._current_session_id is None:
            return

        conn = self._get_connection()
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

    def log_telemetry(self, record: TelemetryRecord) -> None:
        """
        Enqueues a telemetry record for asynchronous batched persistence.
        Non-blocking to ensure GUI / telemetry stream never stalls.
        """
        try:
            self._queue.put_nowait((record, self._current_session_id))
        except queue.Full:
            logger.warning("Telemetry log queue full, dropping record to protect main thread.")

    def _start_writer(self) -> None:
        self._stop_event.clear()
        self._writer_thread = threading.Thread(
            target=self._worker_loop,
            name="VoltesseDBWriter",
            daemon=True,
        )
        self._writer_thread.start()

    def _worker_loop(self) -> None:
        """Background thread loop that drains the queue and writes in batches."""
        conn = self._get_connection()
        batch: List[Tuple] = []
        last_flush_time = time.time()

        insert_sql = """
            INSERT INTO telemetry_logs (
                timestamp, session_id, speed_kmh, motor_rpm, battery_soc,
                battery_voltage, battery_current, battery_power_kw, battery_temp_c,
                motor_temp_c, inverter_temp_c, throttle_pct, brake_pct,
                drive_mode, trip_distance_km, warnings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                # Wait for items with short timeout
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
        conn = self._get_connection()
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

        conn = self._get_connection()
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

    def close(self) -> None:
        """Signals writer thread to finish and flushes remaining records."""
        self._stop_event.set()
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=3.0)
        logger.info("Database manager closed.")
