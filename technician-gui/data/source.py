"""Picks the data source: PostgreSQL when VOLTESSE_DB_URL is set, otherwise the simulator.

The hosted Streamlit demo has no database URL, so it keeps showing simulated data.
"""

import os

USING_DB = bool(os.environ.get("VOLTESSE_DB_URL"))

if USING_DB:
    from data.db import diagnostics_data, get_sessions, latest_metrics, temperature_history  # noqa: F401
else:
    from data.simulator import SESSIONS, diagnostics_data, live_metrics, live_temperature_history  # noqa: F401

    def get_sessions():
        return SESSIONS
