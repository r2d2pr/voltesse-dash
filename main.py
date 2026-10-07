"""
Voltesse Dash - Main Application Entrypoint
Orchestrates the SQLite database logger, multi-mode telemetry streams
(CAN Bus Race Mode, Keyboard Game Simulation Mode, Autonomous Test Mode),
and the PyQt6 driver cockpit GUI.
Supports Automatic and Sequential Manual transmission switching,
as well as runtime write access controls and session export capabilities.
"""

import argparse
import logging
import signal
import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.can_bus_source import CANTelemetrySource
from src.dashboard_gui import VoltesseDashboard
from src.database import DatabaseManager
from src.simulation_source import SimulationTelemetryStream
from src.telemetry_source import MockTelemetryStream

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("voltesse.main")


class VoltesseApp:
    """Application Controller managing lifecycle, operating modes, and signal routing."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("Voltesse Dash")

        # 1. Initialize SQLite Database Manager with write access controls
        logger.info("Initializing Database Manager at %s...", args.db_path)
        read_only = getattr(args, "read_only", False)
        no_logging = getattr(args, "no_logging", False)
        write_enabled = (not read_only) and (not no_logging)

        self.db_manager = DatabaseManager(
            db_path=args.db_path,
            batch_size=args.batch_size,
            flush_interval_sec=args.flush_interval,
            write_enabled=write_enabled,
            read_only=read_only,
        )
        self.session_id = self.db_manager.start_session(initial_soc=88.5)

        # 2. Initialize Distraction-Free Cockpit GUI
        logger.info("Initializing Cockpit GUI...")
        self.gui = VoltesseDashboard()

        # Reflect database write logging state on top HUD ribbon
        self.gui.set_logging_state(
            write_enabled=self.db_manager.is_write_enabled(),
            read_only=self.db_manager.read_only,
        )

        # Fullscreen by default as specified in design requirements
        if args.windowed:
            logger.info("Launching in windowed development mode...")
            self.gui.show()
        else:
            logger.info("Launching in fullscreen cockpit mode...")
            self.gui.showFullScreen()

        # 3. Initialize Three Telemetry Sources
        logger.info("Initializing Telemetry Sources (Race CAN, Game Sim, Test Autonomous)...")
        # Mode 1: Default Race Mode (CAN Bus only)
        self.can_stream = CANTelemetrySource(
            interface=args.can_interface,
            channel=args.can_channel,
            enable_mock_bus=args.can_mock,
        )

        # Mode 2: Interactive Video-Game Simulation Mode
        self.sim_stream = SimulationTelemetryStream(
            update_interval_ms=args.interval_ms
        )

        # Mode 3: Test Mode (Autonomous mock telemetry stream)
        self.test_stream = MockTelemetryStream(
            update_interval_ms=args.interval_ms
        )

        self.current_mode: Optional[str] = None

        # 4. Wire Interactive Signals from GUI
        self.gui.mode_switch_requested.connect(self.switch_mode)
        self.gui.simulation_input_changed.connect(self._handle_sim_inputs)
        self.gui.drive_mode_requested.connect(self._cycle_drive_mode)
        self.gui.gear_shift_requested.connect(self._shift_gear)
        self.gui.transmission_toggle_requested.connect(self._toggle_transmission)
        self.gui.gear_up_requested.connect(self._shift_up)
        self.gui.gear_down_requested.connect(self._shift_down)
        self.gui.logging_toggle_requested.connect(self._toggle_logging)
        self.gui.pause_requested.connect(self._toggle_pause)

        # Connect window close / application quit
        self.app.aboutToQuit.connect(self.shutdown)

        # Track statistics for session summary
        self._max_speed = 0.0
        self._total_distance = 0.0
        self._final_soc = 88.5

        # 5. Activate Default Mode (Default: RACE)
        initial_mode = args.mode.upper() if args.mode else "RACE"
        self.switch_mode(initial_mode)

    def switch_mode(self, mode: str) -> None:
        """
        Dynamically transitions between the three telemetry modes:
        - RACE: CAN Bus direct
        - SIMULATION: Interactive video game controls
        - TEST: Autonomous mock stream
        """
        if mode == self.current_mode:
            return

        logger.info("Switching operating mode to: %s", mode)

        # Disconnect and pause previous active stream
        if self.current_mode == "RACE":
            try:
                self.can_stream.telemetry_received.disconnect(self.gui.update_telemetry)
                self.can_stream.telemetry_received.disconnect(self.db_manager.log_telemetry)
                self.can_stream.telemetry_received.disconnect(self._track_stats)
            except Exception:
                pass
            if self.can_stream.isRunning():
                self.can_stream.stop()

        elif self.current_mode == "SIMULATION":
            try:
                self.sim_stream.telemetry_received.disconnect(self.gui.update_telemetry)
                self.sim_stream.telemetry_received.disconnect(self.db_manager.log_telemetry)
                self.sim_stream.telemetry_received.disconnect(self._track_stats)
            except Exception:
                pass
            if self.sim_stream.isRunning():
                self.sim_stream.stop()

        elif self.current_mode == "TEST":
            try:
                self.test_stream.telemetry_received.disconnect(self.gui.update_telemetry)
                self.test_stream.telemetry_received.disconnect(self.db_manager.log_telemetry)
                self.test_stream.telemetry_received.disconnect(self._track_stats)
            except Exception:
                pass
            if self.test_stream.isRunning():
                self.test_stream.stop()

        # Connect and start the new active stream
        self.current_mode = mode
        if mode == "RACE":
            self.can_stream.telemetry_received.connect(self.gui.update_telemetry)
            self.can_stream.telemetry_received.connect(self.db_manager.log_telemetry)
            self.can_stream.telemetry_received.connect(self._track_stats)
            if not self.can_stream.isRunning():
                self.can_stream.start()

        elif mode == "SIMULATION":
            self.sim_stream.telemetry_received.connect(self.gui.update_telemetry)
            self.sim_stream.telemetry_received.connect(self.db_manager.log_telemetry)
            self.sim_stream.telemetry_received.connect(self._track_stats)
            if not self.sim_stream.isRunning():
                self.sim_stream.start()

        elif mode == "TEST":
            self.test_stream.telemetry_received.connect(self.gui.update_telemetry)
            self.test_stream.telemetry_received.connect(self.db_manager.log_telemetry)
            self.test_stream.telemetry_received.connect(self._track_stats)
            if not self.test_stream.isRunning():
                self.test_stream.start()

        # Inform GUI of operating mode change
        self.gui.set_operating_mode(mode)

    def _handle_sim_inputs(self, throttle: bool, brake: bool, steer_l: bool, steer_r: bool) -> None:
        """Dispatches active driving controls to simulation stream."""
        if self.current_mode == "SIMULATION":
            self.sim_stream.set_inputs(
                throttle=throttle,
                brake=brake,
                steer_left=steer_l,
                steer_right=steer_r,
            )

    def _cycle_drive_mode(self) -> None:
        """Cycles vehicle drive modes (ECO -> DRIVE -> SPORT)."""
        if self.current_mode == "RACE":
            new_mode = self.can_stream.cycle_drive_mode()
            logger.info("Race CAN drive mode set to: %s", new_mode)
        elif self.current_mode == "SIMULATION":
            new_mode = self.sim_stream.cycle_drive_mode()
            logger.info("Simulation drive mode set to: %s", new_mode)
        elif self.current_mode == "TEST":
            new_mode = self.test_stream.cycle_drive_mode()
            logger.info("Test drive mode set to: %s", new_mode)

    def _toggle_transmission(self) -> None:
        """Toggles between AUTO and MANUAL transmission (restricted to Race and Sim modes)."""
        if self.current_mode == "RACE":
            new_mode = self.can_stream.toggle_transmission_mode()
            logger.info("Race CAN transmission mode toggled to: %s", new_mode)
        elif self.current_mode == "SIMULATION":
            new_mode = self.sim_stream.toggle_transmission_mode()
            logger.info("Simulation transmission mode toggled to: %s", new_mode)
        elif self.current_mode == "TEST":
            logger.warning("Transmission toggle rejected: TEST mode is restricted to AUTO.")

    def _shift_up(self) -> None:
        """Shifts up sequentially in manual mode, or advances selector in auto mode."""
        if self.current_mode == "RACE":
            new_gear = self.can_stream.shift_up()
            logger.info("Race CAN shifted up to: %s", new_gear)
        elif self.current_mode == "SIMULATION":
            new_gear = self.sim_stream.shift_up()
            logger.info("Sim shifted up to: %s", new_gear)
        elif self.current_mode == "TEST":
            new_gear = self.test_stream.shift_up()
            logger.info("Test shifted up to: %s", new_gear)

    def _shift_down(self) -> None:
        """Shifts down sequentially in manual mode, or reverses selector in auto mode."""
        if self.current_mode == "RACE":
            new_gear = self.can_stream.shift_down()
            logger.info("Race CAN shifted down to: %s", new_gear)
        elif self.current_mode == "SIMULATION":
            new_gear = self.sim_stream.shift_down()
            logger.info("Sim shifted down to: %s", new_gear)
        elif self.current_mode == "TEST":
            new_gear = self.test_stream.shift_down()
            logger.info("Test shifted down to: %s", new_gear)

    def _shift_gear(self) -> None:
        """Cycles gears forward (G key)."""
        if self.current_mode == "RACE":
            new_gear = self.can_stream.shift_gear()
            logger.info("Race CAN gear shifted to: %s", new_gear)
        elif self.current_mode == "SIMULATION":
            new_gear = self.sim_stream.shift_gear()
            logger.info("Sim gear shifted to: %s", new_gear)
        elif self.current_mode == "TEST":
            new_gear = self.test_stream.shift_gear()
            logger.info("Test gear shifted to: %s", new_gear)

    def _toggle_logging(self) -> None:
        """Toggles database write access on and off at runtime via hotkey L."""
        if self.db_manager.read_only:
            self.gui.status_badge.setText("⚠️ DATABASE IN READ-ONLY MODE")
            self.gui.status_badge.setStyleSheet(
                "background-color: rgba(255, 184, 0, 0.25); color: #FFB800; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
            )
            return

        current_state = self.db_manager.is_write_enabled()
        new_state = self.db_manager.set_write_access(not current_state)
        self.gui.set_logging_state(new_state, self.db_manager.read_only)
        if new_state:
            if self.db_manager._current_session_id is None:
                self.session_id = self.db_manager.start_session(initial_soc=self._final_soc)
            self.gui.status_badge.setText("DATABASE LOGGING ACTIVE")
            self.gui.status_badge.setStyleSheet(
                "background-color: rgba(0, 245, 160, 0.20); color: #00F5A0; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
            )
        else:
            self.gui.status_badge.setText("DATABASE LOGGING PAUSED")
            self.gui.status_badge.setStyleSheet(
                "background-color: rgba(255, 184, 0, 0.20); color: #FFB800; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
            )

    def _toggle_pause(self) -> None:
        """Pauses or resumes the active stream (Space key)."""
        if self.current_mode == "RACE":
            p = self.can_stream.toggle_pause()
            logger.info("CAN stream paused: %s", p)
        elif self.current_mode == "SIMULATION":
            p = self.sim_stream.toggle_pause()
            logger.info("Simulation stream paused: %s", p)
        elif self.current_mode == "TEST":
            p = self.test_stream.toggle_pause()
            logger.info("Test stream paused: %s", p)

    def _track_stats(self, record) -> None:
        if record.speed_kmh > self._max_speed:
            self._max_speed = record.speed_kmh
        self._total_distance = record.trip_distance_km
        self._final_soc = record.battery_soc

    def start(self) -> int:
        """Enters Qt event loop."""
        logger.info("Voltesse Dash started successfully in %s mode.", self.current_mode)
        return self.app.exec()

    def shutdown(self) -> None:
        """Clean shutdown handler ensuring threads and DB connections flush."""
        logger.info("Shutting down Voltesse Dash...")

        for stream in (self.can_stream, self.sim_stream, self.test_stream):
            if stream.isRunning():
                stream.stop()

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
        "--mode",
        type=str,
        default="RACE",
        choices=["RACE", "SIMULATION", "TEST"],
        help="Initial telemetry operating mode (default: RACE - CAN Bus)",
    )
    parser.add_argument(
        "--can-interface",
        type=str,
        default=None,
        help="CAN interface driver (e.g. socketcan, virtual, pcan)",
    )
    parser.add_argument(
        "--can-channel",
        type=str,
        default=None,
        help="CAN channel name (e.g. can0, vcan0)",
    )
    parser.add_argument(
        "--can-mock",
        action="store_true",
        help="Enable mock CAN transmitter for bench testing without live vehicle ECU",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/voltesse_telemetry.db",
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Open SQLite database in strict read-only mode (disables session and telemetry writes)",
    )
    parser.add_argument(
        "--no-logging",
        action="store_true",
        help="Launch with telemetry database logging disabled initially (toggleable via key L)",
    )
    parser.add_argument(
        "--export-csv",
        type=int,
        metavar="SESSION_ID",
        default=None,
        help="Export a specific trip session to CSV and exit",
    )
    parser.add_argument(
        "--export-json",
        type=int,
        metavar="SESSION_ID",
        default=None,
        help="Export a specific trip session to JSON and exit",
    )
    parser.add_argument(
        "--export-summary",
        action="store_true",
        help="Export summary of all trip sessions to CSV and exit",
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=40,
        help="Telemetry poll interval in milliseconds (default: 40ms = 25Hz)",
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
        "--windowed",
        action="store_true",
        help="Launch in windowed mode rather than fullscreen (default: fullscreen)",
    )
    return parser.parse_args()


def main() -> None:
    # Allow Ctrl+C to terminate application cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    args = parse_args()

    # Handle direct database export commands if requested
    if args.export_csv is not None or args.export_json is not None or args.export_summary:
        db = DatabaseManager(db_path=args.db_path, read_only=True)
        try:
            if args.export_csv is not None:
                path = db.export_session_to_csv(args.export_csv)
                print(f"Exported session {args.export_csv} to CSV: {path}")
            if args.export_json is not None:
                path = db.export_session_to_json(args.export_json)
                print(f"Exported session {args.export_json} to JSON: {path}")
            if args.export_summary:
                path = db.export_all_sessions_summary_csv()
                print(f"Exported all sessions summary to CSV: {path}")
        except Exception as e:
            print(f"Export failed: {e}")
            sys.exit(1)
        finally:
            db.close()
        sys.exit(0)

    voltesse_app = VoltesseApp(args)
    sys.exit(voltesse_app.start())


if __name__ == "__main__":
    main()
