from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.db import (
    authenticate_user,
    get_diagnostics_data,
    get_live_metrics,
    get_live_temperature_history,
    get_recent_sessions,
    test_connection,
)


class DatabaseModuleTests(unittest.TestCase):
    def test_test_connection_handles_offline_gracefully(self):
        ok, msg = test_connection()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)

    def test_authenticate_demo_fallback(self):
        ok, user = authenticate_user("tech_demo", "Demo123!")
        self.assertTrue(ok)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "tech_demo")

    def test_authenticate_invalid_credentials(self):
        ok, user = authenticate_user("invalid_user", "wrong_password")
        self.assertFalse(ok)
        self.assertIsNone(user)

    def test_recent_sessions_fallback(self):
        sessions, is_db = get_recent_sessions(limit=5)
        self.assertIsInstance(sessions, list)
        self.assertGreater(len(sessions), 0)
        self.assertIn("id", sessions[0])
        self.assertIn("date", sessions[0])
        self.assertIn("max_temp", sessions[0])

    def test_live_metrics_fallback(self):
        metrics, is_db = get_live_metrics()
        self.assertIn("speed", metrics)
        self.assertIn("rpm", metrics)
        self.assertIn("battery", metrics)
        self.assertIn("temperature", metrics)

    def test_live_temperature_history_fallback(self):
        times, temps, is_db = get_live_temperature_history(seconds=30)
        self.assertGreater(len(times), 0)
        self.assertEqual(len(times), len(temps))

    def test_diagnostics_data_fallback(self):
        data, is_db = get_diagnostics_data()
        self.assertIn("speeds", data)
        self.assertIn("efficiency", data)
        self.assertIn("motor_temps", data)
        self.assertIn("power_draws", data)


if __name__ == "__main__":
    unittest.main()
