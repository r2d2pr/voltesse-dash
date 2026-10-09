"""Unit tests using Python's standard-library unittest."""

import unittest

from data.simulator import (
    SESSIONS, diagnostics_data, live_metrics, live_temperature_history,
)


class SimulatorTests(unittest.TestCase):
    def test_live_history_matches_metric_card(self):
        times, temperatures = live_temperature_history(30)
        self.assertEqual(len(times), 31)
        self.assertEqual(temperatures[-1], live_metrics(30)["temperature"])
        times, temperatures = live_temperature_history(120)
        self.assertEqual(len(times), 61)
        self.assertEqual(temperatures[-1], live_metrics(120)["temperature"])

    def test_session_variations(self):
        runs = {session["id"]: diagnostics_data(session) for session in SESSIONS}
        idx60 = runs["#14"]["speeds"].index(60)
        self.assertEqual(runs["#14"]["efficiency"][idx60], 135.0)
        self.assertEqual(runs["#13"]["efficiency"][idx60], 143.0)
        self.assertEqual(runs["#14"]["trend_power"][4], 6200)
        self.assertEqual(runs["#12"]["trend_power"][4], 5400)
        self.assertEqual(runs["#14"]["battery_levels"][-1], 74.0)
        self.assertEqual(runs["#11"]["battery_levels"][-1], 70.0)

    def test_temperature_curve_reaches_session_max(self):
        for session in SESSIONS:
            data = diagnostics_data(session)
            self.assertAlmostEqual(data["temp_rise"][-1], session["max_temp"], places=1)
            self.assertEqual(len(data["temp_rise"]), len(data["time_minutes"]))


if __name__ == "__main__":
    unittest.main()
