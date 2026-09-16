"""
Unit and integration tests for Voltesse Dash components:
- SQLite Database & Asynchronous Batch Writer
- Mock Telemetry Stream
- PyQt6 Cockpit GUI initialization and rendering
"""

import os
import shutil
import tempfile
import time
import unittest

from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtWidgets import QApplication

from src.database import DatabaseManager, TelemetryRecord
from src.telemetry_source import MockTelemetryStream
from src.dashboard_gui import VoltesseDashboard


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

        # Log 12 records
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
            )
            self.db.log_telemetry(rec)

        # Wait briefly for batch writer thread
        time.sleep(0.6)

        recent = self.db.get_recent_telemetry(limit=50)
        self.assertEqual(len(recent), 12)
        self.assertEqual(recent[0]["drive_mode"], "DRIVE")

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
        )

        gui.update_telemetry(rec)
        self.assertEqual(gui.speed_gauge.current_val, 88.0)
        self.assertEqual(gui.battery_widget.soc, 75.4)
        self.assertEqual(gui.trip_dist_val.text(), "14.25 km")
        self.assertEqual(gui.mode_badge.text(), "SPORT")
        self.assertIn("HIGH SPEED", gui.status_badge.text())


if __name__ == "__main__":
    unittest.main()
