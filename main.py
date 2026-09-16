"""
Voltesse Dash - Main Application Entrypoint
Orchestrates the SQLite database logger, asynchronous mock telemetry stream,
and the PyQt6 driver cockpit GUI.
"""

import argparse
import logging
import signal
import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.dashboard_gui import VoltesseDashboard
from src.database import DatabaseManager
from src.telemetry_source import MockTelemetryStream

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("voltesse.main")


class VoltesseApp:
    """Application Controller managing lifecycle and signal connections."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Voltesse Dash")

        # 1. Initialize SQLite Database Manager with asynchronous batched writes
        logger.info("Initializing Database Manager...")
        self.db_manager = DatabaseManager(
            db_path=args.db_path,
            batch_size=args.batch_size,
            flush_interval_sec=args.flush_interval,
        )
        self.session_id = self.db_manager.start_session(initial_soc=88.5)

        # 2. Initialize Distraction-Free Cockpit GUI
        logger.info("Initializing Cockpit GUI...")
        self.gui = VoltesseDashboard()
        if args.fullscreen:
            self.gui.showFullScreen()
        else:
            self.gui.show()

        # 3. Initialize Asynchronous Mock Telemetry Stream (QThread)
        logger.info("Initializing Mock Telemetry Stream...")
        self.telemetry_stream = MockTelemetryStream(
            update_interval_ms=args.interval_ms
        )

        # 4. Wire Signals & Slots
        # Connect telemetry stream to GUI (runs on UI thread via Qt signal-slot)
        self.telemetry_stream.telemetry_received.connect(self.gui.update_telemetry)

        # Connect telemetry stream to SQLite batched logger
        self.telemetry_stream.telemetry_received.connect(self.db_manager.log_telemetry)

        # Connect bench-test interactive signals
        self.gui.drive_mode_requested.connect(self._cycle_drive_mode)
        self.gui.pause_requested.connect(self._toggle_pause)

        # Connect window close / application quit
        self.app.aboutToQuit.connect(self.shutdown)

        # Track statistics for session summary
        self._max_speed = 0.0
        self._total_distance = 0.0
        self._final_soc = 88.5
        self.telemetry_stream.telemetry_received.connect(self._track_stats)

    def _cycle_drive_mode(self) -> None:
        new_mode = self.telemetry_stream.cycle_drive_mode()
        logger.info("Drive mode changed to: %s", new_mode)

    def _toggle_pause(self) -> None:
        is_paused = self.telemetry_stream.toggle_pause()
        logger.info("Telemetry stream paused: %s", is_paused)

    def _track_stats(self, record) -> None:
        if record.speed_kmh > self._max_speed:
            self._max_speed = record.speed_kmh
        self._total_distance = record.trip_distance_km
        self._final_soc = record.battery_soc

    def start(self) -> int:
        """Starts background telemetry stream and enters Qt event loop."""
        logger.info("Starting telemetry stream QThread...")
        self.telemetry_stream.start()

        logger.info("Voltesse Dash started successfully.")
        return self.app.exec()

    def shutdown(self) -> None:
        """Clean shutdown handler ensuring threads and DB connections flush."""
        logger.info("Shutting down Voltesse Dash...")

        if self.telemetry_stream.isRunning():
            self.telemetry_stream.stop()

        # Complete trip session in database
        self.db_manager.end_session(
            final_soc=self._final_soc,
            max_speed=self._max_speed,
            avg_speed=0.0,
            distance_km=self._total_distance,
            energy_kwh=0.0,
        )

        # Flush batched writes and close database
        self.db_manager.close()
        logger.info("Shutdown complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Voltesse Dash Embedded Telemetry Cockpit")
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/voltesse_telemetry.db",
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=50,
        help="Telemetry poll interval in milliseconds (default: 50ms = 20Hz)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Number of records to batch before committing to SQLite",
    )
    parser.add_argument(
        "--flush-interval",
        type=float,
        default=1.0,
        help="Max time in seconds between database batch commits",
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Launch in fullscreen mode (recommended for embedded display)",
    )
    return parser.parse_args()


def main() -> None:
    # Allow Ctrl+C to terminate application cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    args = parse_args()
    voltesse_app = VoltesseApp(args)
    sys.exit(voltesse_app.start())


if __name__ == "__main__":
    main()
