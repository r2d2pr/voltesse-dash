# Voltesse Dash ⚡

A high-performance digital cockpit instrument cluster and local telemetry logging engine designed for embedded systems (e.g., Raspberry Pi) and EV powertrains. Built with **Python**, **PyQt6**, and **SQLite**.

---

## Features

- **Distraction-Free Cockpit UI**: High-contrast, zero-touch driver dashboard tailored for embedded automotive screens.
  - **Dynamic Arc Speedometer**: Antialiased radial gauge showing vehicle speed (km/h) and real-time motor RPM.
  - **Bidirectional Power / Regen Meter**: Instantaneous power delivery (kW) and regenerative braking recapture indicators.
  - **Battery State of Charge (SoC)**: Segmented high-visibility battery gauge, pack voltage (V), current draw (A), and estimated range.
  - **Thermal Diagnostics**: Live temperature monitoring for motor, inverter, and battery pack with threshold alert badges.
  - **Rolling Telemetry Trace**: Real-time sparkline graph plotting speed and power curves.
- **Asynchronous Telemetry Engine**: Physics-based simulated EV powertrain running on a dedicated `QThread` (20 Hz default).
- **Batched SQLite Persistence**: Thread-safe background writer utilizing `WAL` mode and micro-batched commits to eliminate I/O bottlenecks and protect SD card flash memory.

---

## Project Structure

```
voltesse-dash/
├── data/                      # Local SQLite databases (auto-created)
├── src/
│   ├── __init__.py
│   ├── dashboard_gui.py       # PyQt6 digital cluster interface & custom widgets
│   ├── database.py            # SQLite schema and batched async writer
│   └── telemetry_source.py    # EV physics & mock telemetry stream (QThread)
├── tests/
│   └── test_voltesse.py       # Unit and integration test suite
├── main.py                    # Application lifecycle orchestrator
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

---

## Getting Started

### 1. Prerequisites

- Python 3.10+
- Virtual environment (recommended)

### 2. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/r2d2pr/voltesse-dash.git
cd voltesse-dash

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# or: .venv\Scripts\activate     # Windows

# Install requirements
pip install -r requirements.txt
```

### 3. Launching the Dashboard

Run the main application:

```bash
python main.py
```

#### Command-Line Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--fullscreen` | `False` | Launches dashboard in fullscreen mode (recommended for embedded displays) |
| `--interval-ms` | `50` | Telemetry poll interval in milliseconds (50ms = 20 Hz) |
| `--batch-size` | `25` | Number of telemetry records to batch before SQLite commit |
| `--flush-interval`| `1.0` | Max seconds between database batch flushes |
| `--db-path` | `data/voltesse_telemetry.db` | Path to the SQLite database file |

Example with options:
```bash
python main.py --fullscreen --interval-ms 25 --batch-size 50
```

---

## Bench Testing & Hotkeys

For bench testing and desktop development without vehicle hardware:

| Key | Action |
| :--- | :--- |
| `M` | Cycle drive modes (`ECO` ➔ `DRIVE` ➔ `SPORT`) |
| `Space` | Pause / Resume telemetry stream |
| `F11` | Toggle fullscreen mode |
| `Esc` / `Q` | Graceful application shutdown |

---

## Running Tests

Execute the automated test suite with Python's built-in `unittest`:

```bash
python -m unittest discover tests
```

---

## License

MIT License. See `LICENSE` for details.
