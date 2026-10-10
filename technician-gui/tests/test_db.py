"""Checks data/db.py returns what the pages expect. Needs the local database:
VOLTESSE_DB_URL=postgresql://voltesse:voltesse@localhost:5432/voltesse_dash python -m unittest discover tests
"""

import os
import unittest


@unittest.skipUnless(os.environ.get("VOLTESSE_DB_URL"), "VOLTESSE_DB_URL not set")
class DatabaseSourceTests(unittest.TestCase):
    def test_same_shape_as_simulator(self):
        from data import db, simulator

        sessions = db.get_sessions()
        self.assertTrue(sessions, "the database has no sessions to check")
        data = db.diagnostics_data(sessions[0])
        self.assertEqual(data.keys(), simulator.diagnostics_data().keys())
        for x, y in [("speeds", "efficiency"), ("motor_temps", "power_draws"),
                     ("distances", "battery_levels"), ("motor_rpms", "power_values"),
                     ("time_minutes", "temp_rise")]:
            self.assertEqual(len(data[x]), len(data[y]), f"{x} / {y}")
        self.assertIn(len(data["trend_power"]), (0, len(data["motor_temps"])))


if __name__ == "__main__":
    unittest.main()
