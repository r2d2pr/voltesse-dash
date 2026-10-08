"""
Unit and integration tests for Voltesse Dash components:
- PostgreSQL Database (SRS schema) & Asynchronous Batch Writer with Granular Write Access, Retention & Exports
- CAN Bus Race Mode Telemetry Source & Frame Decoding
- Interactive Video Game Simulation Telemetry Stream
- Autonomous Mock Telemetry Stream (Test Mode)
- PyQt6 Cockpit GUI initialization, mode switching, and auto-scaling
- Automatic (PRNDB with dynamic D1-D6 gear display) and Manual Transmission
- Application Mode Orchestrator & Logging Controls
"""

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import time
import unittest
import uuid

import psycopg

from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from main import VoltesseApp
from src.can_bus_source import (
    CANTelemetrySource,
    CAN_ID_SPEED_MOTOR,
    CAN_ID_BATTERY,
    CAN_ID_THERMALS_WARN,
)
from src.database import DatabaseManager, TelemetryRecord
from src.dashboard_gui import VoltesseDashboard, TPMSWidget, AwdTorqueVectorWidget
from src.simulation_source import SimulationTelemetryStream
from src.telemetry_source import MockTelemetryStream

try:
    import can
except ImportError:
    can = None


# ---------------------------------------------------------------------
# PostgreSQL test database support
# Set VOLTESSE_TEST_DB_URL to a database the tests may create schemas in, e.g.
#   postgresql://voltesse:password@localhost:5432/voltesse_test
# Every test gets its own temporary schema, so tests never touch real data.
# ---------------------------------------------------------------------
TEST_DB_URL = os.environ.get(
    "VOLTESSE_TEST_DB_URL", "postgresql://voltesse:voltesse@localhost:5432/voltesse_test"
)


def _test_db_available() -> bool:
    try:
        psycopg.connect(TEST_DB_URL, connect_timeout=2).close()
        return True
    except psycopg.Error:
        return False


DB_AVAILABLE = _test_db_available()
SKIP_NO_DB = unittest.skipUnless(DB_AVAILABLE, "PostgreSQL test database not reachable (set VOLTESSE_TEST_DB_URL)")


def create_isolated_schema():
    """Creates a throwaway schema and returns (schema_name, connection_url_using_it)."""
    name = "t_" + uuid.uuid4().hex[:12]
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{name}"')
    separator = "&" if "?" in TEST_DB_URL else "?"
    return name, f"{TEST_DB_URL}{separator}options=-csearch_path%3D{name}"


def drop_isolated_schema(name: str) -> None:
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')


def make_record(**overrides) -> "TelemetryRecord":
    values = dict(
        timestamp=time.time(),
        speed_kmh=50.0,
        motor_rpm=4000,
        battery_soc=90.0,
        battery_voltage=398.0,
        battery_current=25.0,
        battery_power_kw=10.0,
        battery_temp_c=31.0,
        motor_temp_c=45.0,
        inverter_temp_c=40.0,
        throttle_pct=30.0,
        brake_pct=0.0,
        drive_mode="DRIVE",
        trip_distance_km=0.5,
        warnings=[],
    )
    values.update(overrides)
    return TelemetryRecord(**values)


@SKIP_NO_DB
class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.schema, self.db_url = create_isolated_schema()
        self.db = DatabaseManager(db_url=self.db_url, batch_size=5, flush_interval_sec=0.2)

    def tearDown(self):
        self.db.close()
        drop_isolated_schema(self.schema)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_schema_and_batched_logging(self):
        session_id = self.db.start_session(initial_soc=90.0)
        self.assertIsNotNone(session_id)

        # Log 12 records with gear and transmission_mode
        for i in range(12):
            rec = TelemetryRecord(
                timestamp=time.time(),
                speed_kmh=50.0 + i,
                motor_rpm=4000 + i * 50,
                battery_soc=90.0 - (i * 0.1),
                battery_voltage=398.0,
                battery_current=25.0,
                battery_power_kw=9.95,
                battery_temp_c=31.0,
                motor_temp_c=45.0,
                inverter_temp_c=40.0,
                throttle_pct=30.0,
                brake_pct=0.0,
                drive_mode="DRIVE",
                trip_distance_km=0.5 * i,
                warnings=[],
                steering_angle=0.0,
                gear="3" if i >= 6 else "D2",
                transmission_mode="MANUAL" if i >= 6 else "AUTO",
            )
            self.assertTrue(self.db.log_telemetry(rec))

        time.sleep(0.6)

        recent = self.db.get_recent_telemetry(limit=50)
        self.assertEqual(len(recent), 12)
        self.assertEqual(recent[0]["drive_mode"], "DRIVE")
        self.assertIn("gear", recent[0])
        self.assertIn("transmission_mode", recent[0])

        summary = self.db.get_trip_summary(session_id)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["sample_count"], 12)

        self.db.end_session(
            final_soc=88.8,
            max_speed=61.0,
            avg_speed=55.5,
            distance_km=5.5,
            energy_kwh=1.2,
        )

    def test_write_access_controls(self):
        # 1. Verify initially enabled
        self.assertTrue(self.db.is_write_enabled())

        rec = TelemetryRecord(
            timestamp=time.time(),
            speed_kmh=60.0,
            motor_rpm=4500,
            battery_soc=85.0,
            battery_voltage=395.0,
            battery_current=30.0,
            battery_power_kw=11.8,
            battery_temp_c=30.0,
            motor_temp_c=42.0,
            inverter_temp_c=38.0,
            throttle_pct=25.0,
            brake_pct=0.0,
            drive_mode="DRIVE",
            trip_distance_km=1.0,
            warnings=[],
        )

        # 2. Disable write access dynamically
        self.assertFalse(self.db.set_write_access(False))
        self.assertFalse(self.db.is_write_enabled())

        # Writes must be rejected
        self.assertFalse(self.db.log_telemetry(rec))

        # 3. Re-enable write access
        self.assertTrue(self.db.set_write_access(True))
        self.assertTrue(self.db.is_write_enabled())
        self.assertTrue(self.db.log_telemetry(rec))

    def test_read_only_mode_enforcement(self):
        ro_db = DatabaseManager(db_url=self.db_url, read_only=True)
        self.assertTrue(ro_db.read_only)
        self.assertFalse(ro_db.is_write_enabled())

        # Attempting session creation returns None
        self.assertIsNone(ro_db.start_session(95.0))

        # Attempting write returns False
        rec = TelemetryRecord(
            timestamp=time.time(),
            speed_kmh=20.0,
            motor_rpm=1500,
            battery_soc=90.0,
            battery_voltage=400.0,
            battery_current=5.0,
            battery_power_kw=2.0,
            battery_temp_c=25.0,
            motor_temp_c=30.0,
            inverter_temp_c=28.0,
            throttle_pct=10.0,
            brake_pct=0.0,
            drive_mode="DRIVE",
            trip_distance_km=0.1,
            warnings=[],
        )
        self.assertFalse(ro_db.log_telemetry(rec))

        # Cannot force enable write access in read_only mode
        self.assertFalse(ro_db.set_write_access(True))
        self.assertFalse(ro_db.is_write_enabled())

        ro_db.close()

    def test_export_csv_and_json(self):
        session_id = self.db.start_session(initial_soc=89.0)
        rec = TelemetryRecord(
            timestamp=time.time(),
            speed_kmh=75.5,
            motor_rpm=5800,
            battery_soc=88.5,
            battery_voltage=394.0,
            battery_current=42.0,
            battery_power_kw=16.5,
            battery_temp_c=31.5,
            motor_temp_c=47.0,
            inverter_temp_c=39.0,
            throttle_pct=45.0,
            brake_pct=0.0,
            drive_mode="SPORT",
            trip_distance_km=2.5,
            warnings=["HIGH SPEED"],
            gear="D3",
            transmission_mode="AUTO",
        )
        self.db.log_telemetry(rec)
        time.sleep(0.4)
        self.db.end_session(88.0, 75.5, 70.0, 2.5, 0.4)

        # 1. Export CSV
        csv_file = os.path.join(self.test_dir, "export_session.csv")
        out_csv = self.db.export_session_to_csv(session_id, output_path=csv_file)
        self.assertTrue(os.path.exists(out_csv))
        with open(out_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertIn("speed_mph", header)
            self.assertIn("battery_percent", header)
            self.assertIn("gear", header)
            row = next(reader)
            self.assertGreater(len(row), 5)

        # 2. Export JSON
        json_file = os.path.join(self.test_dir, "export_session.json")
        out_json = self.db.export_session_to_json(session_id, output_path=json_file)
        self.assertTrue(os.path.exists(out_json))
        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("session", data)
            self.assertIn("telemetry", data)
            self.assertEqual(data["record_count"], 1)
            self.assertEqual(data["telemetry"][0]["drive_mode"], "SPORT")

        # 3. Export all sessions summary
        summary_csv = os.path.join(self.test_dir, "all_summary.csv")
        out_sum = self.db.export_all_sessions_summary_csv(output_path=summary_csv)
        self.assertTrue(os.path.exists(out_sum))

    def test_srs_columns_and_units(self):
        """Readings are stored with SRS names/units: mph, watts, battery percent, warning list."""
        self.db.set_signal_status("CAN ACTIVE")
        session_id = self.db.start_session(initial_soc=90.0)
        self.assertTrue(
            self.db.log_telemetry(
                make_record(speed_kmh=100.0, battery_power_kw=10.0, battery_soc=150.0, warnings=["HIGH TEMP"])
            )
        )
        time.sleep(0.6)

        row = self.db.get_recent_telemetry(limit=1)[0]
        self.assertEqual(row["session_id"], session_id)
        self.assertAlmostEqual(row["speed_mph"], 62.1371, places=2)
        self.assertAlmostEqual(row["power_draw_watts"], 10000.0, places=1)
        self.assertEqual(row["battery_percent"], 100.0)  # out-of-range sensor value is clamped
        self.assertEqual(row["warning_state"], ["HIGH TEMP"])
        self.assertEqual(row["signal_status"], "CAN ACTIVE")
        self.assertEqual(row["motor_temperature"], 45.0)

    def test_every_reading_belongs_to_a_session(self):
        """With no session active, logging starts one (TELEMETRY_LOG.session_id is NOT NULL)."""
        self.assertTrue(self.db.log_telemetry(make_record()))
        time.sleep(0.6)
        sessions = self.db.get_all_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(self.db.get_recent_telemetry(limit=5)[0]["session_id"], sessions[0]["session_id"])

    def test_session_lifecycle_and_interrupted_sessions(self):
        first = self.db.start_session(initial_soc=95.0)
        # Simulate a crash: the first session is never ended, then a new run starts.
        self.db._current_session_id = None
        second = self.db.start_session(initial_soc=80.0)
        self.assertNotEqual(first, second)
        self.db.end_session(75.0, 100.0, 50.0, 3.0, 0.5)

        by_id = {s["session_id"]: s for s in self.db.get_all_sessions()}
        self.assertEqual(by_id[first]["status"], "INTERRUPTED")
        self.assertIsNotNone(by_id[first]["end_timestamp"])
        self.assertEqual(by_id[second]["status"], "COMPLETED")
        self.assertAlmostEqual(by_id[second]["max_speed_mph"], 62.1371, places=2)
        self.assertEqual(by_id[second]["end_soc_percent"], 75.0)

    def test_source_change_marks_session_mixed(self):
        self.db.set_source_type("CAN_BUS")
        session_id = self.db.start_session()
        self.db.set_source_type("SIMULATION")
        session = [s for s in self.db.get_all_sessions() if s["session_id"] == session_id][0]
        self.assertEqual(session["source_type"], "MIXED")

    def test_session_based_retention(self):
        for i in range(5):
            self.db.start_session(initial_soc=90.0)
            self.db.log_telemetry(make_record(speed_kmh=10.0 + i))
            time.sleep(0.5)  # let the writer flush this session's reading
            self.db.end_session(89.0, 20.0, 10.0, 1.0, 0.1)

        self.assertEqual(len(self.db.get_all_sessions()), 5)
        self.assertEqual(self.db.prune_old_sessions(keep_sessions=2), 3)

        remaining = self.db.get_all_sessions()
        self.assertEqual(len(remaining), 2)
        # Telemetry of pruned sessions is removed with them (no orphans).
        readings = self.db.get_recent_telemetry(limit=100)
        self.assertEqual(len(readings), 2)
        self.assertEqual({r["session_id"] for r in readings}, {s["session_id"] for s in remaining})

    def test_retention_never_deletes_active_session(self):
        self.db.start_session()
        self.assertEqual(self.db.prune_old_sessions(keep_sessions=1), 0)
        self.assertEqual(len(self.db.get_all_sessions()), 1)

    def test_recent_window_returns_last_15_seconds(self):
        session_id = self.db.start_session()
        base = time.time() - 60
        for offset in (0, 10, 20, 30):
            self.db.log_telemetry(make_record(timestamp=base + offset))
        time.sleep(0.8)

        window = self.db.get_recent_window(session_id, seconds=15)
        self.assertEqual(len(window), 2)  # readings at +20 s and +30 s
        self.assertLessEqual(window[0]["timestamp"], window[1]["timestamp"])


class TestCANTelemetrySource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test_gui", "-platform", "offscreen"])

    def test_can_frame_decoding(self):
        source = CANTelemetrySource()

        # Mock frame 1: 0x100 (Speed=72.5 km/h, RPM=5690, Thr=65%, Brk=0%, Mode=2/SPORT)
        speed_raw = 725
        rpm_raw = 5690
        thr_raw = 65
        brk_raw = 0
        mode_code = 2
        f1_data = struct.pack(">HHBBBx", speed_raw, rpm_raw, thr_raw, brk_raw, mode_code)
        if can is not None:
            msg1 = can.Message(arbitration_id=CAN_ID_SPEED_MOTOR, data=f1_data)
            source._decode_message(msg1)

            self.assertEqual(source.speed_kmh, 72.5)
            self.assertEqual(source.motor_rpm, 5690)
            self.assertEqual(source.throttle_pct, 65.0)
            self.assertEqual(source.brake_pct, 0.0)
            self.assertEqual(source.drive_mode, "SPORT")

            # Mock frame 2: 0x101 (SoC=85.0%, Volt=392.5V, Curr=55.0A, Dist=12.4 km)
            f2_data = struct.pack(">HHhH", 850, 3925, 550, 124)
            msg2 = can.Message(arbitration_id=CAN_ID_BATTERY, data=f2_data)
            source._decode_message(msg2)

            self.assertEqual(source.battery_soc, 85.0)
            self.assertEqual(source.battery_voltage, 392.5)
            self.assertEqual(source.battery_current, 55.0)
            self.assertEqual(source.trip_distance_km, 12.4)

            # Mock frame 3: 0x102 (BattT=32C, MotT=48C, InvT=41C, Amb=22C, Warn=0x01/LOW_BATT, Steer=-15.5 deg)
            f3_data = struct.pack(">BBBBHh", 32 + 40, 48 + 40, 41 + 40, 22 + 40, 1, -155)
            msg3 = can.Message(arbitration_id=CAN_ID_THERMALS_WARN, data=f3_data)
            source._decode_message(msg3)

            self.assertEqual(source.battery_temp_c, 32.0)
            self.assertEqual(source.motor_temp_c, 48.0)
            self.assertEqual(source.inverter_temp_c, 41.0)
            self.assertEqual(source.ambient_temp_c, 22.0)
            self.assertIn("LOW BATTERY", source.warnings)
            self.assertEqual(source.steering_angle, -15.5)

            rec = source._build_record()
            self.assertIsInstance(rec, TelemetryRecord)
            self.assertEqual(rec.speed_kmh, 72.5)
            self.assertEqual(rec.steering_angle, -15.5)

    def test_can_transmission_and_gears(self):
        source = CANTelemetrySource()
        self.assertEqual(source.transmission_mode, "AUTO")
        self.assertEqual(source.current_gear, "D1")

        # Cycle drive mode in Race mode
        self.assertEqual(source.drive_mode, "DRIVE")
        self.assertEqual(source.cycle_drive_mode(), "SPORT")
        self.assertEqual(source.cycle_drive_mode(), "ECO")
        self.assertEqual(source.cycle_drive_mode(), "DRIVE")

        # Toggle to MANUAL
        mode = source.toggle_transmission_mode()
        self.assertEqual(mode, "MANUAL")
        self.assertEqual(source.transmission_mode, "MANUAL")
        self.assertEqual(source.current_gear, "1")

        # Shift up sequentially
        new_g = source.shift_up()
        self.assertEqual(new_g, "2")

        # Shift down
        down_g = source.shift_down()
        self.assertEqual(down_g, "1")

        # Toggle back to AUTO -> speed-matched D1
        mode = source.toggle_transmission_mode()
        self.assertEqual(mode, "AUTO")
        self.assertEqual(source.current_gear, "D1")


class TestSimulationTelemetryStream(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test_gui", "-platform", "offscreen"])

    def test_interactive_video_game_physics(self):
        sim = SimulationTelemetryStream(update_interval_ms=10)

        # 1. Test Acceleration input (W / Up key pressed)
        sim.set_inputs(throttle=True, brake=False, steer_left=False, steer_right=False)
        for _ in range(15):
            sim._step_game_physics(dt=0.05, k_thr=True, k_brk=False, k_left=False, k_right=False)

        self.assertGreater(sim.throttle_pct, 50.0)
        self.assertGreater(sim.speed_kmh, 1.0)
        self.assertGreater(sim.motor_rpm, 50)
        self.assertGreater(sim.battery_current, 10.0)

        # 2. Test Braking input (S / Down key pressed)
        speed_before_brake = sim.speed_kmh
        sim.set_inputs(throttle=False, brake=True, steer_left=False, steer_right=False)
        for _ in range(15):
            sim._step_game_physics(dt=0.05, k_thr=False, k_brk=True, k_left=False, k_right=False)

        self.assertEqual(sim.throttle_pct, 0.0)
        self.assertGreater(sim.brake_pct, 50.0)
        self.assertLess(sim.speed_kmh, speed_before_brake)

        # 3. Test Steering input (A / Left key pressed)
        sim.set_inputs(throttle=False, brake=False, steer_left=True, steer_right=False)
        for _ in range(10):
            sim._step_game_physics(dt=0.05, k_thr=False, k_brk=False, k_left=True, k_right=False)
        self.assertLess(sim.steering_angle, -10.0)

        # Test self-centering steering spring (no keys pressed)
        sim.set_inputs(throttle=False, brake=False, steer_left=False, steer_right=False)
        for _ in range(20):
            sim._step_game_physics(dt=0.05, k_thr=False, k_brk=False, k_left=False, k_right=False)
        self.assertAlmostEqual(sim.steering_angle, 0.0, places=1)

        # 4. Drive mode cycle
        self.assertEqual(sim.drive_mode, "DRIVE")
        self.assertEqual(sim.cycle_drive_mode(), "SPORT")
        self.assertEqual(sim.cycle_drive_mode(), "ECO")
        self.assertEqual(sim.cycle_drive_mode(), "DRIVE")

        # 5. Gear shifting
        self.assertEqual(sim.shift_gear("R"), "R")
        self.assertEqual(sim.current_gear, "R")

    def test_simulation_manual_transmission(self):
        sim = SimulationTelemetryStream(update_interval_ms=10)
        self.assertEqual(sim.transmission_mode, "AUTO")
        self.assertEqual(sim.current_gear, "D1")

        # Test automatic speed-to-gear mapping
        self.assertEqual(sim.get_auto_gear_for_speed(15.0), 1)
        self.assertEqual(sim.get_auto_gear_for_speed(40.0), 2)
        self.assertEqual(sim.get_auto_gear_for_speed(65.0), 3)
        self.assertEqual(sim.get_auto_gear_for_speed(95.0), 4)
        self.assertEqual(sim.get_auto_gear_for_speed(130.0), 5)
        self.assertEqual(sim.get_auto_gear_for_speed(165.0), 6)

        # Toggle to MANUAL
        new_mode = sim.toggle_transmission_mode()
        self.assertEqual(new_mode, "MANUAL")
        self.assertEqual(sim.current_gear, "1")

        # Upshift: 1 -> 2 -> 3 -> 4 -> 5 -> 6
        self.assertEqual(sim.shift_up(), "2")
        self.assertEqual(sim.shift_up(), "3")
        self.assertEqual(sim.shift_up(), "4")
        self.assertEqual(sim.shift_up(), "5")
        self.assertEqual(sim.shift_up(), "6")
        # Cannot shift past 6
        self.assertEqual(sim.shift_up(), "6")

        # Downshift: 6 -> 5 -> 4 -> 3 -> 2 -> 1 -> N -> R
        self.assertEqual(sim.shift_down(), "5")
        self.assertEqual(sim.shift_down(), "4")
        self.assertEqual(sim.shift_down(), "3")
        self.assertEqual(sim.shift_down(), "2")
        self.assertEqual(sim.shift_down(), "1")
        self.assertEqual(sim.shift_down(), "N")
        self.assertEqual(sim.shift_down(), "R")
        # Cannot shift below R
        self.assertEqual(sim.shift_down(), "R")

        # Toggle back to AUTO
        back_mode = sim.toggle_transmission_mode()
        self.assertEqual(back_mode, "AUTO")
        self.assertEqual(sim.current_gear, "R")


class TestMockTelemetryStream(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test_gui", "-platform", "offscreen"])

    def test_telemetry_generation(self):
        stream = MockTelemetryStream(update_interval_ms=10)
        records = []

        def on_record(rec):
            records.append(rec)

        stream.telemetry_received.connect(on_record)
        stream.start()

        for _ in range(25):
            time.sleep(0.01)
            QApplication.processEvents()

        stream.stop()
        QApplication.processEvents()

        self.assertGreater(len(records), 5)
        first = records[0]
        self.assertIsInstance(first, TelemetryRecord)
        self.assertGreaterEqual(first.battery_soc, 0.0)
        self.assertLessEqual(first.battery_soc, 100.0)
        # Test mode is always AUTO transmission
        self.assertEqual(first.transmission_mode, "AUTO")

    def test_mock_gear_cycling(self):
        stream = MockTelemetryStream(update_interval_ms=10)
        # Selector shifts PRNDB in Test Mode
        self.assertEqual(stream.shift_gear("P"), "P")
        self.assertEqual(stream.shift_gear("R"), "R")
        self.assertEqual(stream.shift_gear("N"), "N")
        self.assertEqual(stream.shift_gear("B"), "B")
        self.assertEqual(stream.shift_up(), "B")  # B is top of PRNDB
        self.assertEqual(stream.shift_down(), "D1")  # previous from B is D (speed 0 -> D1)


class TestDashboardGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test_gui", "-platform", "offscreen"])

    def test_gui_telemetry_update(self):
        gui = VoltesseDashboard()
        rec = TelemetryRecord(
            timestamp=time.time(),
            speed_kmh=88.0,
            motor_rpm=6900,
            battery_soc=75.4,
            battery_voltage=392.1,
            battery_current=45.2,
            battery_power_kw=17.7,
            battery_temp_c=32.4,
            motor_temp_c=58.2,
            inverter_temp_c=49.1,
            throttle_pct=55.0,
            brake_pct=0.0,
            drive_mode="SPORT",
            trip_distance_km=14.25,
            warnings=["HIGH SPEED"],
            steering_angle=-12.5,
            gear="4",
            transmission_mode="MANUAL",
        )

        gui.update_telemetry(rec)
        self.assertEqual(gui.speed_gauge.current_val, 88.0)
        self.assertEqual(gui.speed_gauge.steering_angle, -12.5)
        self.assertEqual(gui.speed_gauge.active_gear, "4")
        self.assertEqual(gui.speed_gauge.transmission_mode, "MANUAL")
        self.assertIn("MANUAL [M4]", gui.trans_mode_badge.text())
        self.assertEqual(gui.battery_widget.soc, 75.4)
        self.assertEqual(gui.trip_dist_val.text(), "14.25 km")
        self.assertEqual(gui.mode_badge.text(), "SPORT")
        self.assertIn("HIGH SPEED", gui.status_badge.text())

        # Test TPMS & AWD widgets
        self.assertGreater(gui.tpms_widget.fl_bar, 2.0)
        self.assertEqual(gui.awd_widget.bias_mode, "RWD BIAS")
        self.assertEqual(gui.awd_widget.rear_pct, 70.0)

        # Test Auto mode gear label update
        rec_auto = TelemetryRecord(
            timestamp=time.time(),
            speed_kmh=62.0,
            motor_rpm=4800,
            battery_soc=74.0,
            battery_voltage=392.0,
            battery_current=30.0,
            battery_power_kw=11.7,
            battery_temp_c=32.0,
            motor_temp_c=55.0,
            inverter_temp_c=46.0,
            throttle_pct=40.0,
            brake_pct=0.0,
            drive_mode="DRIVE",
            trip_distance_km=15.0,
            warnings=[],
            steering_angle=0.0,
            gear="D3",
            transmission_mode="AUTO",
        )
        gui.update_telemetry(rec_auto)
        self.assertEqual(gui.speed_gauge.active_gear, "D3")
        self.assertEqual(gui.speed_gauge.transmission_mode, "AUTO")
        self.assertIn("AUTO [D3]", gui.trans_mode_badge.text())

    def test_gui_mode_switching_and_scaling(self):
        gui = VoltesseDashboard()

        # Mode switches
        gui.set_operating_mode("RACE")
        self.assertIn("RACE", gui.op_mode_badge.text())

        gui.set_operating_mode("SIMULATION")
        self.assertIn("SIMULATION", gui.op_mode_badge.text())
        self.assertIn("T:TRANS", gui.controls_hint.text())

        gui.set_operating_mode("TEST")
        self.assertIn("TEST", gui.op_mode_badge.text())
        self.assertIn("TEST: AUTO ONLY", gui.controls_hint.text())

        # Test auto-scaling on different resolutions
        # 1. 1024x600 (Raspberry Pi display)
        gui.resize(1024, 600)
        gui._apply_dynamic_scale()
        self.assertGreaterEqual(gui.top_bar.height(), 34)

        # 2. 1920x1080 (1080p Fullscreen display)
        gui.resize(1920, 1080)
        gui._apply_dynamic_scale()
        self.assertGreater(gui.top_bar.height(), 36)
        self.assertGreater(gui.brand_label.font().pointSize(), 10)

    def test_gui_logging_badge_and_toggle(self):
        gui = VoltesseDashboard()
        gui.set_logging_state(write_enabled=True, read_only=False)
        self.assertEqual(gui.logging_badge.text(), "REC")

        gui.set_logging_state(write_enabled=False, read_only=False)
        self.assertEqual(gui.logging_badge.text(), "LOG OFF")

        gui.set_logging_state(write_enabled=False, read_only=True)
        self.assertEqual(gui.logging_badge.text(), "R/O")

        # Test 'L' key triggers logging_toggle_requested
        emitted = []
        gui.logging_toggle_requested.connect(lambda: emitted.append(True))
        event_l = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_L, Qt.KeyboardModifier.NoModifier)
        gui.keyPressEvent(event_l)
        self.assertEqual(len(emitted), 1)

    def test_gui_units_and_12h_clock(self):
        gui = VoltesseDashboard()

        # 1. Test 12-hour AM/PM clock display
        gui._update_clock()
        clock_text = gui.clock_label.text()
        self.assertTrue(clock_text.endswith("AM") or clock_text.endswith("PM"), f"Clock text {clock_text} does not end with AM/PM")
        self.assertEqual(clock_text.count(":"), 2)

        # 2. Test initial Metric mode
        self.assertEqual(gui.unit_system, "METRIC")
        self.assertEqual(gui.units_badge.text(), "METRIC")
        self.assertEqual(gui.ambient_label.text(), "22°C")
        self.assertEqual(gui.speed_gauge.unit, "KM/H")
        self.assertEqual(gui.speed_gauge.max_val, 180.0)

        # Feed sample record
        rec = TelemetryRecord(
            timestamp=time.time(),
            speed_kmh=100.0,
            motor_rpm=6000,
            battery_soc=80.0,
            battery_voltage=400.0,
            battery_current=50.0,
            battery_power_kw=20.0,
            battery_temp_c=30.0,
            motor_temp_c=55.0,
            inverter_temp_c=45.0,
            throttle_pct=50.0,
            brake_pct=0.0,
            drive_mode="DRIVE",
            steering_angle=0.0,
            trip_distance_km=10.0,
            warnings=[],
            gear="D4",
            transmission_mode="AUTO",
        )
        gui.update_telemetry(rec)
        self.assertIn("km", gui.trip_dist_val.text())
        self.assertEqual(round(gui.speed_gauge.current_val), 100)

        # 3. Test Toggle to Imperial via key 'U'
        units_signals = []
        gui.units_changed.connect(lambda u: units_signals.append(u))

        event_u = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_U, Qt.KeyboardModifier.NoModifier)
        gui.keyPressEvent(event_u)

        self.assertEqual(gui.unit_system, "IMPERIAL")
        self.assertEqual(gui.units_badge.text(), "IMPERIAL")
        self.assertEqual(gui.ambient_label.text(), "72°F")
        self.assertEqual(gui.speed_gauge.unit, "MPH")
        self.assertEqual(gui.speed_gauge.max_val, 120.0)
        self.assertEqual(gui.battery_widget.unit_system, "IMPERIAL")
        self.assertEqual(gui.tpms_widget.unit_system, "IMPERIAL")
        self.assertEqual(gui.thermal_widget.unit_system, "IMPERIAL")
        self.assertEqual(gui.awd_widget.unit_system, "IMPERIAL")
        self.assertEqual(gui.sparkline_widget.unit_system, "IMPERIAL")

        # Telemetry should be converted to imperial values
        self.assertIn("mi", gui.trip_dist_val.text())
        # 100 km/h * 0.621371 = ~62.1 mph
        self.assertEqual(round(gui.speed_gauge.current_val), 62)
        self.assertEqual(units_signals, ["IMPERIAL"])

        # 4. Toggle back to Metric
        gui.keyPressEvent(event_u)
        self.assertEqual(gui.unit_system, "METRIC")
        self.assertEqual(gui.units_badge.text(), "METRIC")
        self.assertEqual(gui.ambient_label.text(), "22°C")
        self.assertEqual(gui.speed_gauge.unit, "KM/H")
        self.assertEqual(round(gui.speed_gauge.current_val), 100)
        self.assertIn("km", gui.trip_dist_val.text())
        self.assertEqual(units_signals, ["IMPERIAL", "METRIC"])

    def test_transmission_toggle_restriction(self):
        gui = VoltesseDashboard()
        signals_received = []

        gui.transmission_toggle_requested.connect(lambda: signals_received.append("TOGGLE"))

        # In RACE mode, key 'T' emits transmission toggle
        gui.set_operating_mode("RACE")
        event_t = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_T, Qt.KeyboardModifier.NoModifier)
        gui.keyPressEvent(event_t)
        self.assertEqual(len(signals_received), 1)

        # In SIMULATION mode, key 'T' emits transmission toggle
        gui.set_operating_mode("SIMULATION")
        gui.keyPressEvent(event_t)
        self.assertEqual(len(signals_received), 2)

        # In TEST mode, key 'T' must NOT emit transmission toggle and must show warning
        gui.set_operating_mode("TEST")
        gui.keyPressEvent(event_t)
        self.assertEqual(len(signals_received), 2)  # Still 2, not incremented!
        self.assertIn("TEST MODE: AUTO ONLY", gui.status_badge.text())

        # Shifting keys (E, C)
        shifts = []
        gui.gear_up_requested.connect(lambda: shifts.append("UP"))
        gui.gear_down_requested.connect(lambda: shifts.append("DOWN"))

        event_e = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)
        gui.keyPressEvent(event_e)
        self.assertEqual(shifts, ["UP"])

        event_c = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier)
        gui.keyPressEvent(event_c)
        self.assertEqual(shifts, ["UP", "DOWN"])

        # Test mode hotkeys including KeypadModifier
        modes_switched = []
        gui.mode_switch_requested.connect(lambda m: modes_switched.append(m))
        event_k1 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_1, Qt.KeyboardModifier.KeypadModifier)
        gui.keyPressEvent(event_k1)
        self.assertEqual(modes_switched, ["RACE"])

        event_k2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_2, Qt.KeyboardModifier.KeypadModifier)
        gui.keyPressEvent(event_k2)
        self.assertEqual(modes_switched, ["RACE", "SIMULATION"])


@SKIP_NO_DB
class TestVoltesseAppModes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test_gui", "-platform", "offscreen"])

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.schema, self.db_url = create_isolated_schema()

    def tearDown(self):
        drop_isolated_schema(self.schema)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_app_mode_transitions_and_transmission(self):
        args = argparse.Namespace(
            mode="RACE",
            can_interface=None,
            can_channel=None,
            can_mock=False,
            db_url=self.db_url,
            interval_ms=10,
            batch_size=5,
            flush_interval=0.2,
            windowed=True,
            read_only=False,
            no_logging=False,
        )
        app = VoltesseApp(args)

        self.assertEqual(app.current_mode, "RACE")
        self.assertEqual(app.gui.current_mode, "RACE")
        self.assertTrue(app.db_manager.is_write_enabled())

        # Test runtime logging toggle
        app._toggle_logging()
        self.assertFalse(app.db_manager.is_write_enabled())
        self.assertEqual(app.gui.logging_badge.text(), "LOG OFF")
        app._toggle_logging()
        self.assertTrue(app.db_manager.is_write_enabled())
        self.assertEqual(app.gui.logging_badge.text(), "REC")

        # Test transmission toggle in RACE mode
        self.assertEqual(app.can_stream.transmission_mode, "AUTO")
        app._toggle_transmission()
        self.assertEqual(app.can_stream.transmission_mode, "MANUAL")
        app._toggle_transmission()
        self.assertEqual(app.can_stream.transmission_mode, "AUTO")

        # Switch to SIMULATION
        app.switch_mode("SIMULATION")
        self.assertEqual(app.current_mode, "SIMULATION")
        self.assertEqual(app.gui.current_mode, "SIMULATION")

        # Test transmission toggle in SIMULATION mode
        self.assertEqual(app.sim_stream.transmission_mode, "AUTO")
        app._toggle_transmission()
        self.assertEqual(app.sim_stream.transmission_mode, "MANUAL")
        self.assertEqual(app.sim_stream.current_gear, "1")

        # Test manual upshift and downshift
        app._shift_up()
        self.assertEqual(app.sim_stream.current_gear, "2")
        app._shift_down()
        self.assertEqual(app.sim_stream.current_gear, "1")

        # Send simulation inputs
        app._handle_sim_inputs(throttle=True, brake=False, steer_l=False, steer_r=True)
        self.assertTrue(app.sim_stream._key_throttle)
        self.assertTrue(app.sim_stream._key_steer_right)

        # Switch to TEST
        app.switch_mode("TEST")
        self.assertEqual(app.current_mode, "TEST")
        self.assertEqual(app.gui.current_mode, "TEST")

        # Test mode blocks transmission toggle
        app._toggle_transmission()
        self.assertEqual(app.test_stream.current_gear, "D1")

        app.shutdown()

    def test_app_read_only_and_no_logging_flags(self):
        # 1. Test --no-logging flag
        args_nl = argparse.Namespace(
            mode="TEST",
            can_interface=None,
            can_channel=None,
            can_mock=False,
            db_url=self.db_url,
            interval_ms=10,
            batch_size=5,
            flush_interval=0.2,
            windowed=True,
            read_only=False,
            no_logging=True,
        )
        app_nl = VoltesseApp(args_nl)
        self.assertFalse(app_nl.db_manager.is_write_enabled())
        self.assertEqual(app_nl.gui.logging_badge.text(), "LOG OFF")
        app_nl.shutdown()

        # 2. Test --read-only flag
        args_ro = argparse.Namespace(
            mode="TEST",
            can_interface=None,
            can_channel=None,
            can_mock=False,
            db_url=self.db_url,
            interval_ms=10,
            batch_size=5,
            flush_interval=0.2,
            windowed=True,
            read_only=True,
            no_logging=False,
        )
        app_ro = VoltesseApp(args_ro)
        self.assertTrue(app_ro.db_manager.read_only)
        self.assertFalse(app_ro.db_manager.is_write_enabled())
        self.assertEqual(app_ro.gui.logging_badge.text(), "R/O")
        # Trying to toggle logging in read-only mode is blocked
        app_ro._toggle_logging()
        self.assertFalse(app_ro.db_manager.is_write_enabled())
        app_ro.shutdown()

    def test_app_imperial_units_flag(self):
        args_imp = argparse.Namespace(
            mode="RACE",
            can_interface=None,
            can_channel=None,
            can_mock=False,
            db_url=self.db_url,
            interval_ms=10,
            batch_size=5,
            flush_interval=0.2,
            windowed=True,
            read_only=False,
            no_logging=False,
            imperial=True,
            units="imperial",
        )
        app_imp = VoltesseApp(args_imp)
        self.assertEqual(app_imp.gui.unit_system, "IMPERIAL")
        self.assertEqual(app_imp.gui.units_badge.text(), "IMPERIAL")
        self.assertEqual(app_imp.gui.speed_gauge.unit, "MPH")

        # Toggle at runtime
        app_imp.gui.toggle_units()
        self.assertEqual(app_imp.gui.unit_system, "METRIC")
        self.assertEqual(app_imp.gui.units_badge.text(), "METRIC")
        self.assertEqual(app_imp.gui.speed_gauge.unit, "KM/H")

        app_imp.shutdown()


if __name__ == "__main__":
    unittest.main()
