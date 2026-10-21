# Voltesse Dash ⚡ v4.0.0

[![Version](https://img.shields.io/badge/version-4.0.0-00F5A0.svg)](https://github.com/r2d2pr/voltesse-dash)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/PyQt-6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Web](https://img.shields.io/badge/Streamlit-1.65-red.svg)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![CAN](https://img.shields.io/badge/CAN-SocketCAN%20%7C%20virtual-orange.svg)](https://python-can.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern automotive digital cockpit, web-based technician admin portal, and local telemetry logging engine for embedded displays, including Raspberry Pi, and EV powertrains. Version 4.0 delivers **Full-Width Dedicated Widget Pages** (Speedometer, Battery & Energy Diagnostics, Powertrain Dynamics, and TPMS), **Intuitive Left ⇄ Right Page Navigation** (`◄` / `►` arrow keys, `V` hotkey, and interactive touch chevrons), **Top HUD Speed Fallback** when away from the speedometer, and a **pinned constant bottom telemetry deck** (trip odometer and powertrain thermals). Built with **Python**, **PyQt6**, **Streamlit**, **python-can**, and **PostgreSQL**.

---

## What's New in Version 4.0 🚀

- 📄 **Full-Width Dedicated Widget Pages (Individual Cockpit Views)**:
  - Designed specifically for compact embedded screens (e.g., 800×480 Raspberry Pi touchscreens) where crowded multi-column layouts cause visual clutter. Each primary widget now commands the full central stage with clean breathing room, zero clipping, and authentic automotive typography:
    - **Page 1 (SPEED)**: Full-stage radial speedometer dial with digital speed numerals, PRNDB capsule, active dynamic EV gear, motor RPM, steering angle, and throttle/brake meters.
    - **Page 2 (BATTERY)**: High-voltage battery & energy diagnostics featuring a large glowing circular SoC gauge, range estimation HUD (`km`/`mi`), 4 pack diagnostic chips (Cell Avg, Health SOH, Charge Limit, Peak Temp), and a 4-quadrant electrical grid (Pack Voltage, Current Draw, Net Power, Energy Consumption).
    - **Page 3 (POWERTRAIN)**: Dual-motor AWD torque vectoring dynamics, front/rear distribution bars with real-time torque in Nm (or lb-ft), center-zero bidirectional Power/Regen bar, and live telemetry wave chart.
    - **Page 4 (TPMS)**: Full-width tire pressure monitoring system with EV chassis blueprint, 4 corner diagnostic cards with dashed guide lines, individual tire pressures, and temperatures.
- ↔️ **Intuitive Left ⇄ Right Page Switching**:
  - **Arrow Keys `◄` / `►`**: Instant page flipping left or right.
  - **Hotkey `V`**: Quick single-key page cycle (`SPEED` ➔ `BATTERY` ➔ `POWERTRAIN` ➔ `TPMS`).
  - **Interactive Top HUD Navigator**: Touch-screen friendly `◄` and `►` buttons with live page indicator pill (`◄ SPEED [1/4] ►`, `◄ BATTERY [2/4] ►`, `◄ POWERTRAIN [3/4] ►`, `◄ TPMS [4/4] ►`).
- 🛡️ **Top HUD Driver Safety Speed Fallback**:
  - When viewing Pages 2, 3, or 4 (navigated away from the speedometer), the Top HUD displays a high-visibility compact digital speed pill (e.g. `104 KM/H [D4]` or `65 MPH [M5]`), ensuring the driver is never without essential speed and active gear context.
- ⚓ **Pinned Constant Telemetry Deck**:
  - The bottom deck (Trip Odometer + Powertrain Temperatures: Motor, Inverter, Battery Pack) remains fixed, visible, and constant across all 4 pages.
- ⚡ **Instant Frame-1 Display Initialization**:
  - Eliminated startup black screen delay under Cage/Wayland kiosks by displaying the cockpit window immediately on frame 1 before executing database or network handshakes.
- ⚙️ **CLI Flags for Custom Startup Views**:
  - `--view {speed,battery,powertrain,tpms}`: Configure the initial startup page.

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
- **Dual Metric & Imperial Unit Architecture**:
  - Global runtime switching via hotkey `U` dynamically transforms all cluster telemetry readouts across Race, Sim, and Test modes:
    - **Speed**: `KM/H` (0–180 scale) ⇄ `MPH` (0–120 scale)
    - **Estimated Range & Trip Odometer**: `km` ⇄ `mi`
    - **Thermal Temperatures (Motor, Inverter, Battery Pack)**: `°C` ⇄ `°F`
    - **4-Wheel Tire Pressure (TPMS)**:  `bar` ⇄ `psi`
    - **Dual-Motor Torque Vectoring**: `Nm` ⇄ `lb-ft`
  - Top HUD ribbon features a dedicated `[METRIC]` / `[IMPERIAL]` badge for instantaneous driver awareness.
- **12-Hour AM/PM Precision Cockpit Clock**:
  - Top HUD ribbon clock formatted in 12-hour AM/PM format with live second tracking, synchronized across all operating modes.
- **Granular Database Write Access & Storage Controls**:
  - **Pre-flight Write Verification**: Verifies connection and write permissions before logging.
  - **Runtime Write Toggle (`L` key)**: Drivers can pause and resume database logging on the fly without stopping vehicle telemetry or restarting the dashboard.
  - **Top Ribbon Status Indicator**: Live status badge shows `REC` (active writing), `LOG OFF` (writing paused), or `R/O` (strict read-only).
  - **Strict Read-Only Enforcement (`--read-only`)**: Safe post-race diagnostics without modifying existing trip sessions or records.
  - **Session Data Export**: Export trip sessions directly to CSV or structured JSON via CLI flags (`--export-csv`, `--export-json`, `--export-summary`).
- **Fullscreen & Dynamic Auto-Scaling (800x480 to 4K)**:
  - Runs in **fullscreen mode by default** on launch.
  - Dynamically adapts to 800x480 Raspberry Pi touchscreens, 1024x600 displays, 720p, 1080p, 1440p, and 4K monitors without layout distortion.
- **Distraction-Free Cyber-Mint Cockpit UI**:
  - **Dynamic Radial Speedometer**: Central gauge with digital speed numerals, motor RPM, gear capsule, dual throttle/brake micro-meters, and steering angle readout.
  - **Battery & Range Hero**: High-visibility SoC arc, pack voltage (V), current (A), and estimated range (km/mi).
  - **Bidirectional Power / Regen Bar**: Live kW delivery and regenerative braking recapture indicators.
  - **4-Wheel TPMS Monitoring Pod**: Top-down chassis schematic tracking corner tire pressures and temperatures.
  - **AWD Dynamic Torque Vectoring Pod**: Real-time front and rear motor torque allocation with mode bias.
  - **Thermal Diagnostics Pod**: Continuous monitoring for motor, inverter, and battery pack temperatures.
  - **Live Oscilloscope Trace**: Rolling sparkline graph plotting speed and power curves.
- **Asynchronous Telemetry & Batched Logging**:
  - Dedicated `QThread` telemetry sources guarantee zero main GUI thread blocking.
  - PostgreSQL persistence (schema from the SRS, section 3.4) with micro-batched background writes, preventing I/O bottlenecks and protecting SD card flash storage.
  - Session-based retention keeps the newest N vehicle sessions (`--keep-sessions`).

---

## Project Structure

```
voltesse-dash/
├── db/                        # PostgreSQL schema, sample seed data, Docker Compose, backup/migration scripts
│   ├── schema.sql             # Relational SRS schema (technician_user, vehicle_session, telemetry_log, backup_log)
│   ├── seed.sql               # Seed sample telemetry and sessions
│   ├── docker-compose.yml     # Local PostgreSQL 16 container definition
│   └── README.md              # Database setup and Raspberry Pi migration guide
├── data/
│   └── exports/               # Generated CSV & JSON session dumps (auto-created)
├── src/
│   ├── __init__.py            # Package version (v3.0.1)
│   ├── can_bus_source.py      # CAN Bus interface, frame decoders, and synchronized mock transmitter
│   ├── simulation_source.py   # Video-game interactive EV dynamics engine (W/A/S/D, 6-speed manual, D1-D6 auto)
│   ├── telemetry_source.py    # Autonomous EV driving cycle telemetry stream (Test Mode, D1-D6 auto)
│   ├── dashboard_gui.py       # PyQt6 digital cluster interface & 800x480 auto-scaling engine
│   └── database.py            # PostgreSQL persistence: batched writer, sessions, retention, write controls, exports
├── technician-gui/            # Streamlit technician & admin web interface
│   ├── app.py                 # Streamlit entrypoint and navigation controller
│   ├── data/
│   │   ├── db.py              # PostgreSQL database queries, authentication & telemetry feed
│   │   └── simulator.py       # Deterministic fallback simulator for bench testing
│   ├── ui/                    # Modular UI pages (Live, Diagnostics, Sessions, Settings, Login)
│   ├── tests/                 # Unit tests for database integration and simulator
│   └── requirements.txt       # Streamlit dependencies (streamlit, pandas, plotly, psycopg)
├── tests/
│   └── test_voltesse.py       # Comprehensive unit and integration test suite (25 tests)
├── main.py                    # Application lifecycle, transmission, and mode controller
├── requirements.txt           # Driver cockpit dependencies (PyQt6, python-can, psycopg)
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
| `U` | **Toggle Units (Metric ⮂ Imperial)** | Global (Race, Sim, Test) |
| `Left Arrow` | **Previous Cockpit Page (Left ◄)** | Global (Race, Sim, Test) |
| `Right Arrow` | **Next Cockpit Page (Right ►)** | Global (Race, Sim, Test) |
| `V` | **Cycle Cockpit Pages** (`Speed` ➔ `Battery` ➔ `Powertrain` ➔ `TPMS`) | Global (Race, Sim, Test) |
| `X` | **Swap Wing Views (Alternate Layout)** | Global (Race, Sim, Test) |
| `L` | **Toggle Database Logging / Write Access** (`REC` ⮂ `LOG OFF`) | Global |
| `-` / `_` | **Zoom Out UI** (reduce cockpit scale by 5%) | Global |
| `+` / `=` | **Zoom In UI** (increase cockpit scale by 5%) | Global |
| `0` | **Reset UI Zoom** to default (100%) | Global |
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
- PostgreSQL 16 (local installation or Docker)

### 2. Installation

```bash
git clone https://github.com/r2d2pr/voltesse-dash.git
cd voltesse-dash

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# or: .venv\Scripts\activate     # Windows

# Install driver cockpit dependencies
pip install -r requirements.txt

# Or install ALL dependencies (Cockpit + Technician Web Portal)
pip install -r requirements-all.txt

# Start the local PostgreSQL database (see db/README.md for details)
cd db && cp .env.example .env && docker compose up -d && cd ..
export VOLTESSE_DB_URL=postgresql://voltesse:voltesse@localhost:5432/voltesse_dash
# or (Windows PowerShell): $env:VOLTESSE_DB_URL="postgresql://voltesse:voltesse@localhost:5432/voltesse_dash"
```

### 3. Launching the Driver Cockpit

```bash
# Launch in default Fullscreen Race Mode (CAN Bus) - auto-scales to Raspberry Pi 800x480
python main.py

# Launch in windowed development mode with interactive simulation
python main.py --windowed --mode SIMULATION

# Launch with Imperial units enabled by default (MPH, °F, psi, lb-ft)
python main.py --imperial

# Launch with database logging initially paused (toggle on with key L)
python main.py --no-logging

# Launch in strict read-only database mode (disables session and telemetry writes)
python main.py --read-only

# Launch in Race Mode with mock CAN frame transmitter
python main.py --can-mock

# Launch with custom CAN interface (e.g., Linux SocketCAN)
python main.py --can-interface socketcan --can-channel can0
```

### 4. Launching the Technician / Admin Web App

The Streamlit web portal communicates directly with the PostgreSQL database:

```bash
cd technician-gui
pip install -r requirements.txt
streamlit run app.py
```

Or run from the project root:

```bash
streamlit run technician-gui/app.py
```

Access the web interface at `http://localhost:8501` (or `http://<pi-ip>:8501` on your local network).
- Default demo credentials: `tech_demo` or `demo@voltesse.test` with password `Demo123!`.
- If PostgreSQL is offline, the interface automatically runs in fault-tolerant simulated mode.

---

## Database Export & Inspection Tools

Export session logs directly from the command line without launching the GUI:

```bash
# Export summary of all trip sessions to CSV
python main.py --export-summary

# Export specific trip session (e.g. Session 1) to CSV
python main.py --export-csv 1

# Export specific trip session to structured JSON
python main.py --export-json 1

# Export from a custom database location
python main.py --db-url postgresql://voltesse:voltesse@localhost:5432/voltesse_dash --export-csv 1
```

Generated files are saved directly to `data/exports/`.

### Command-Line Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--mode` | `RACE` | Initial telemetry mode (`RACE`, `SIMULATION`, `TEST`) |
| `--windowed` | `False` | Run in windowed mode (default is fullscreen) |
| `--geometry` | `auto` | Force explicit window resolution `WxH` (e.g. `800x480` on Raspberry Pi) |
| `--screen` | `auto` | Target display name or index (e.g. `DSI-1`, `HDMI-A-1`, `0`, `1`; default: auto-prefer DSI) |
| `--scale` / `--ui-scale` | `auto` | Custom cockpit UI scale factor (e.g. `0.85` for compact screens) |
| `--show-cursor` | `False` | Keep mouse cursor visible (default: hidden for distraction-free cockpit) |
| `--imperial` | `False` | Launch in Imperial units (`MPH`, `mi`, `°F`, `psi`, `lb-ft`) |
| `--view` | `speed` | Initial cockpit page (`speed`, `battery`, `powertrain`, `tpms`) |
| `--swap-wings` | `False` | Swap left and right cockpit wings |
| `--read-only` | `False` | Open the database in strict read-only mode |
| `--no-logging`| `False` | Launch with database writing paused (toggleable with `L`) |
| `--export-csv` | `None` | Export a specific vehicle session ID to CSV and exit |
| `--export-json`| `None` | Export a specific vehicle session ID to JSON and exit |
| `--export-summary`| `False` | Export summary of all vehicle sessions to CSV and exit |
| `--can-interface` | `None` | CAN driver (`socketcan`, `virtual`, `pcan`, etc.) |
| `--can-channel` | `None` | CAN channel name (e.g., `can0`, `vcan0`) |
| `--can-mock` | `False` | Enable background mock CAN frame broadcaster for bench testing |
| `--interval-ms` | `40` | Telemetry poll interval in milliseconds (40ms = 25 Hz) |
| `--batch-size` | `25` | Number of records to batch before a PostgreSQL commit |
| `--flush-interval`| `1.0` | Max seconds between database batch flushes |
| `--db-url` | `$VOLTESSE_DB_URL` | PostgreSQL connection URL |
| `--keep-sessions` | `20` | Keep only newest N sessions at startup (`0` disables pruning) |

---

## Running Tests

Execute the automated test suites with Python's built-in `unittest`:

```bash
# Run cockpit unit and integration tests (includes 800x480 resolution scaling tests)
python -m unittest discover tests

# Run technician web app database and simulation tests
python -m unittest discover technician-gui/tests
```

---

## License

MIT License. Designed and engineered for high-performance EV telemetry systems.
