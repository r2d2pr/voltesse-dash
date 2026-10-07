"""
Unit and integration tests for Voltesse Dash components:
- SQLite Database & Asynchronous Batch Writer
- CAN Bus Race Mode Telemetry Source & Frame Decoding
- Interactive Video Game Simulation Telemetry Stream
- Autonomous Mock Telemetry Stream (Test Mode)
- PyQt6 Cockpit GUI initialization, mode switching, and auto-scaling
- Automatic (PRNDB with dynamic D1-D6 gear display) and Manual Transmission
- Application Mode Orchestrator
"""

import argparse
import os
import shutil
import struct
import tempfile
import time
import unittest

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


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_telemetry.db")
        self.db = DatabaseManager(db_path=self.db_path, batch_size=5, flush_interval_sec=0.2)

    def tearDown(self):
        self.db.close()
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
            self.db.log_telemetry(rec)

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


class TestVoltesseAppModes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test_gui", "-platform", "offscreen"])

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_app.db")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_app_mode_transitions_and_transmission(self):
        args = argparse.Namespace(
            mode="RACE",
            can_interface=None,
            can_channel=None,
            can_mock=False,
            db_path=self.db_path,
            interval_ms=10,
            batch_size=5,
            flush_interval=0.2,
            windowed=True,
        )
        app = VoltesseApp(args)

        self.assertEqual(app.current_mode, "RACE")
        self.assertEqual(app.gui.current_mode, "RACE")

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


if __name__ == "__main__":
    unittest.main()
