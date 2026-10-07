# Voltesse Dash ⚡ v2.0

[![Version](https://img.shields.io/badge/version-2.0.0-00F5A0.svg)](https://github.com/r2d2pr/voltesse-dash)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/PyQt-6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![CAN](https://img.shields.io/badge/CAN-SocketCAN%20%7C%20virtual-orange.svg)](https://python-can.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern, high-contrast automotive digital cockpit instrument cluster and local telemetry logging engine engineered for embedded displays (e.g., Raspberry Pi) and EV powertrains. Built with **Python**, **PyQt6**, **python-can**, and **SQLite**.

---

## What's New in Version 2.0 🚀

- 🏎️ **Tri-Mode Operating Architecture**: Instant switching between **Race Mode** (CAN bus), **Simulation Mode** (interactive keyboard video-game controls), and **Test Mode** (autonomous mock telemetry).
- ⚙️ **Dynamic Automatic Gear Display (`D1`–`D6`)**: In Auto mode, vehicle speed dynamically drives active gear calculation across 6 EV gear ratios (`D1` to `D6`) displayed on the central capsule, gear status hub, and HUD ribbon.
- 🕹️ **6-Speed Sequential Manual Transmission**: Driver-controlled shifting (`E` for upshift, `C` for downshift) covering gears `1`–`6`, `N`, and `R` in both Race and Simulation modes.
- 🖥️ **Variable Fullscreen Auto-Scaling Engine**: Native launch in borderless fullscreen with dynamic proportional scaling that adapts flawlessly across any aspect ratio and resolution (1024x600 RPi, 720p, 1080p, 1440p, 4K).
- ⌨️ **Refined Keyboard Input Engine**: OS auto-repeat filtering (`isAutoRepeat`) on action keys to eliminate toggle bouncing, unified keypad/numpad and function key mappings, and synchronized CAN frame transmission.

---

## Core Features

- **Three Operating Modes**:
  - 🏎️ **Race Mode (Default)**: Direct integration with **CAN Bus** (`SocketCAN` on Linux/RPi, virtual or hardware bus on other platforms). Decodes standard CAN frames for velocity, motor RPM, battery voltage/current/SoC, powertrain thermals, tire pressures/temps, steering angle, warnings, transmission mode, and active gear.
  - 🎮 **Simulation Mode**: Interactive video-game physics simulation mapped to keyboard inputs:
    - **Acceleration**: `W` or `Up Arrow`
    - **Braking & Regen**: `S` or `Down Arrow`
    - **Steering Wheel**: `A` / `Left Arrow` (steer left), `D` / `Right Arrow` (steer right) with self-centering spring dynamics
    - **Sequential Shifting**: `E` (Upshift 1–6), `C` (Downshift 6–1–N–R)
    - **Gear Shift / Cycle**: `G` (PRNDB in Auto, Upshift in Manual)
    - **Drive Mode**: `M` (ECO / DRIVE / SPORT)
  - 🧪 **Test Mode**: Autonomous canned driving cycle simulator pulling dynamic EV metrics from `telemetry_source.py` (restricted to Automatic transmission only).
- **Automatic vs. Sequential Manual Transmission**:
  - Dynamic transmission switching via hotkey `T` supported across **Race Mode** and **Simulation Mode**.
  - **Test Mode Exclusion**: Switching to manual transmission is locked in Test Mode; pressing `T` displays an on-screen warning badge (`⚠️ TEST MODE: AUTO ONLY`) and preserves automatic operation.
  - **Dynamic Automatic Gear Display**:
    - In **Auto Mode**, the active virtual gear is dynamically computed from vehicle velocity across 6 realistic EV gear ratios:
      - `D1`: 0 – 25 km/h
      - `D2`: 25 – 50 km/h
      - `D3`: 50 – 78 km/h
      - `D4`: 78 – 110 km/h
      - `D5`: 110 – 145 km/h
      - `D6`: 145+ km/h
    - Speedometer capsule dynamically reflects the active ratio: `[P] [R] [N] [D3] [B]`.
    - Prominent status hub pill: `AUTO • D3 (GEAR 3)`, `AUTO • PARK [P]`, `AUTO • REGEN [B]`, or `MANUAL • M4 (GEAR 4)`.
    - Top HUD Ribbon: Live `AUTO [D3]` or `MANUAL [M4]` mode badge.
- **Robust Keyboard Handling & Input Responsiveness**:
  - OS auto-repeat filtering (`event.isAutoRepeat()`) prevents rapid toggling/debouncing on action keys (`T`, `M`, `G`, `E`, `C`, `1`, `2`, `3`, `Tab`).
  - Standard number row, function keys (`F1`–`F3`), and numeric keypad (`Numpad 1`–`3`) supported for instant mode switching.
  - Synchronized CAN loopback mock transmitter ensures keyboard gear and transmission changes are not overwritten by background CAN frames in Race mode.
  - Strong window focus policy and mouse click focus reclamation.
- **Fullscreen & Dynamic Auto-Scaling**:
  - Runs in **fullscreen mode by default** on launch.
  - All dial gauges, cards, fonts, battery arcs, TPMS silhouettes, and HUD ribbons dynamically auto-scale to fit any display resolution (1024x600, 720p, 1080p, 1440p, 4K) without vertical stretching.
- **Distraction-Free Cyber-Mint Cockpit UI**:
  - **Dynamic Radial Speedometer**: Central gauge with digital speed numerals, motor RPM, gear capsule, dual throttle/brake micro-meters, and steering angle readout.
  - **Battery & Range Hero**: High-visibility SoC arc, pack voltage (V), current (A), and estimated range (km).
  - **Bidirectional Power / Regen Bar**: Live kW delivery and regenerative braking recapture indicators.
  - **4-Wheel TPMS Monitoring Pod**: Top-down chassis schematic tracking corner tire pressures and temperatures.
  - **AWD Dynamic Torque Vectoring Pod**: Real-time front and rear motor torque allocation (Nm) with mode bias.
  - **Thermal Diagnostics**: Continuous monitoring for motor, inverter, and battery pack temperatures.
  - **Live Oscilloscope Trace**: Rolling sparkline graph plotting speed and power curves.
- **Asynchronous Telemetry & Batched Logging**:
  - Dedicated `QThread` telemetry sources guarantee zero main GUI thread blocking.
  - High-performance SQLite persistence with `WAL` mode and micro-batched writes to safeguard SD card flash memory.

---

## Project Structure

```
voltesse-dash/
├── data/                      # Local SQLite databases (auto-created)
├── src/
│   ├── __init__.py
│   ├── can_bus_source.py      # CAN Bus interface, frame decoders, and synchronized mock transmitter
│   ├── simulation_source.py   # Video-game interactive EV dynamics engine (W/A/S/D, 6-speed manual, D1-D6 auto)
│   ├── telemetry_source.py    # Autonomous EV driving cycle telemetry stream (Test Mode, D1-D6 auto)
│   ├── dashboard_gui.py       # PyQt6 digital cluster interface & auto-scaling widgets
│   └── database.py            # SQLite schema, migrations, and batched async writer
├── tests/
│   └── test_voltesse.py       # Comprehensive unit and integration test suite (11 tests)
├── main.py                    # Application lifecycle, transmission, keyboard router, and mode controller
├── requirements.txt           # Python dependencies (PyQt6, python-can)
├── AGENTS.md                  # Embedded developer rules, architecture contracts & specifications
└── README.md                  # Project documentation
```

---

## Keyboard Controls & Hotkeys

| Key | Function | Mode Availability |
| :--- | :--- | :--- |
| `1` / `F1` / `Num 1` | Switch to **Race Mode (CAN Bus)** | Global |
| `2` / `F2` / `Num 2` | Switch to **Simulation Mode (Keyboard Game)** | Global |
| `3` / `F3` / `Num 3` | Switch to **Test Mode (Autonomous Mock)** | Global |
| `Tab` | Cycle through Operating Modes (Race ➔ Sim ➔ Test) | Global |
| `T` | **Toggle Transmission (Auto ⮂ Manual)** | **Race & Sim Modes** *(Disabled in Test Mode)* |
| `E` | **Upshift** (`1` ➔ `6` in Manual, or selector in Auto) | Global |
| `C` | **Downshift** (`6` ➔ `1` ➔ `N` ➔ `R` in Manual, or selector in Auto) | Global |
| `G` | Cycle Gear (`P-R-N-D-B` in Auto, Upshift in Manual) | Global |
| `W` / `Up Arrow` | Accelerate (Throttle ramp-up) | Simulation Mode |
| `S` / `Down Arrow` | Brake (Regen & Friction brake) | Simulation Mode |
| `A` / `Left Arrow` | Steer Left | Simulation Mode |
| `D` / `Right Arrow` | Steer Right | Simulation Mode |
| `M` | Cycle Drive Mode (`ECO` ➔ `DRIVE` ➔ `SPORT`) | Global (Race, Sim, Test) |
| `Space` | Pause / Resume telemetry stream | Global |
| `F11` | Toggle Fullscreen / Windowed display | Global |
| `Esc` / `Q` | Graceful application shutdown | Global |

---

## Getting Started

### 1. Prerequisites

- Python 3.10+
- Virtual environment (recommended)

### 2. Installation

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

```bash
# Launch in default Fullscreen Race Mode (CAN Bus)
python main.py

# Launch in windowed development mode with interactive simulation
python main.py --windowed --mode SIMULATION

# Launch in Race Mode with synchronized mock CAN frame transmitter
python main.py --can-mock

# Launch with custom CAN interface (e.g., Linux SocketCAN)
python main.py --can-interface socketcan --can-channel can0
```

#### Command-Line Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--mode` | `RACE` | Initial telemetry mode (`RACE`, `SIMULATION`, `TEST`) |
| `--windowed` | `False` | Run in windowed mode (default is fullscreen) |
| `--can-interface` | `None` | CAN driver (`socketcan`, `virtual`, `pcan`, etc.) |
| `--can-channel` | `None` | CAN channel name (e.g., `can0`, `vcan0`) |
| `--can-mock` | `False` | Enable background mock CAN frame broadcaster for bench testing |
| `--interval-ms` | `40` | Telemetry poll interval in milliseconds (40ms = 25 Hz) |
| `--batch-size` | `25` | Number of records to batch before SQLite commit |
| `--flush-interval`| `1.0` | Max seconds between database batch flushes |
| `--db-path` | `data/voltesse_telemetry.db` | Path to SQLite database file |

---

## Running Tests

Execute the automated test suite with Python's built-in `unittest`:

```bash
python -m unittest discover tests
```

---

## License

MIT License. Designed and engineered for high-performance EV telemetry systems.
