# Voltesse Dash ⚡ v6.1.0

> **Authenticated Figma Technician Interface:** See [figma-gui/README.md](figma-gui/README.md) for the React/Vite laptop GUI, FastAPI backend, local setup, and [Figma handoff](figma-gui/FIGMA_HANDOFF.md).

[![Version](https://img.shields.io/badge/version-6.1.0-00F5A0.svg)](https://github.com/r2d2pr/voltesse-dash)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/PyQt-6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Web](https://img.shields.io/badge/FastAPI%20%7C%20React%2019-20Hz%20F1%20Push-00F5D4.svg)](figma-gui/)
[![Database](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![CAN](https://img.shields.io/badge/CAN-SocketCAN%20%7C%20virtual-orange.svg)](https://python-can.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern automotive digital cockpit, web-based technician admin portal, and local telemetry logging engine for embedded displays, including Raspberry Pi, and EV powertrains. Version 6.1.0 delivers technician driver profile assignment with real-time cockpit uplink, single/batch/all session deletion controls, normalized telemetry persistence, and streamlined dashboard settings. Built with **Python**, **PyQt6**, **FastAPI**, **React 19**, **python-can**, and **PostgreSQL**.

---

## What's New in Version 6.1.0 🏁

- 👤 **Driver Profile Assignment & Cockpit Telecommand Uplink**:
  - Live driver name input directly inside Technician Portal on both **Sessions** and **Live Pit-Wall Console** tabs.
  - Two-way UDP telecommand dispatch (`SET_DRIVER_NAME`) to embedded cockpit cluster on loopback port 9872.
  - Persistent database tracking in `vehicle_session.driver_identifier` and ongoing real-time telemetry streaming frames.
- 🗑️ **Comprehensive Session Deletion & Database Management**:
  - Single session deletion with row-level action button `[ 🗑️ ]` and foreign key cascade to `telemetry_log`.
  - Batch multi-select deletion with master select/deselect-all and selected count badge (`Delete Selected ({N})`).
  - One-click danger **Clear All Sessions** database wipe executing `TRUNCATE TABLE telemetry_log, vehicle_session RESTART IDENTITY CASCADE`.
- 🎨 **Technician GUI Streamlining**:
  - Removed redundant cluster OLED simulation dial preview from Settings tab.
  - Added responsive 4-column pit-wall telecommand grid with active driver display and status toast feedback.
- 🧪 **Expanded Unit Test Suite**:
  - 38 automated test cases passing with 100% green status, including coverage for driver updates, cascade deletion, batch deletion, and session clearing.

---

## What's New in Version 6.0.0 🏁

- 🏎️ **Waveshare RS485 CAN HAT Hardware Integration**:
  - Full SocketCAN `can0` support via MCP2515 SPI overlay at 500,000 baud with automated persistent bring-up service (`voltesse-can0.service`).
  - Standard Vector DBC Motorola start-bit alignment in `db/voltesse_ev.dbc` and robust `cantools` named signal decoding.
- ⚡ **Driver Cockpit & OLED Cluster Normalization**:
  - Balanced bottom center readout row: Active Gear (`D1`), Drive Mode (`D`/`S`/`E`), and Odometer with 33+ px clearance to dial bezels and 60+ px side margin.
  - Isolated vertical motor temperature bar from temperature text labels (`320`, `200`, `100`), repositioning thermometer icon and `°F` tag to header.
  - Re-engineered Accel and Brake indicators into a straight vertical precision pedal meter on the cluster flank (`meter_x = cx + 1.09r`) with live percentages (`ACC 45%`, `BRK 80%`).
  - Transitioned persistent DTC faults to authentic ISO 7000-1393 Check Engine / MIL illuminated telltale lamps in the bottom-left corner with multi-code counters.
  - Permanent lock to 3-pod OLED binnacle; eliminated legacy Classic dial theme and high-speed threshold alarms.
- 💻 **Technician Portal & WebSocket Telemetry**:
  - Real-time 20Hz UDP/WebSocket telemetry push to React 19 / Vite technician dashboard on port 8501.
  - ErrorBoundary protection and fixed session table crashes.
  - Full systemd auto-restart persistence via `voltesse-technician.service`.
- 🧪 **Automated Test Suite Verification**:
  - 34 cockpit unit and integration tests passing with 100% green status.

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
      - `D1`: 0 – 16 mph
      - `D2`: 16 – 31 mph
      - `D3`: 31 – 48 mph
      - `D4`: 48 – 68 mph
      - `D5`: 68 – 90 mph
      - `D6`: 90+ mph
    - Speedometer capsule dynamically reflects the active ratio: `[P] [R] [N] [D3] [B]`.
    - Prominent status hub pill: `AUTO • D3 (GEAR 3)`, `AUTO • PARK [P]`, `AUTO • REGEN [B]`, or `MANUAL • M4 (GEAR 4)`.
- **Exclusively Imperial System Telemetry**:
  - Built specifically for Imperial units with zero conversions needed by the driver:
    - **Speed**: `MPH` (0–120 scale)
    - **Estimated Range & Trip Odometer**: `mi`
    - **Thermal Temperatures (Motor, Inverter, Battery Pack)**: `°F`
    - **4-Wheel Tire Pressure (TPMS)**: `psi`
    - **Dual-Motor Torque Vectoring**: `lb-ft`
- **12-Hour AM/PM Precision Cockpit Clock**:
  - Top HUD ribbon clock formatted in 12-hour AM/PM format with live second tracking, synchronized across all operating modes.
- **Continuous Always-Active Telemetry Persistence**:
  - Continuous micro-batched background writes to PostgreSQL (schema from SRS, section 3.4), preventing I/O bottlenecks and protecting SD card flash storage.
  - Strict read-only mode (`--read-only`) available for post-race bench analysis.
  - Session Data Export: Export trip sessions directly to CSV or structured JSON via CLI flags (`--export-csv`, `--export-json`, `--export-summary`).
- **Fullscreen & Dynamic Auto-Scaling (800x480 to 4K)**:
  - Runs in **fullscreen mode by default** on launch.
  - Dynamically adapts to 800x480 Raspberry Pi touchscreens, 1024x600 displays, 720p, 1080p, 1440p, and 4K monitors without layout distortion.
- **Distraction-Free Cyber-Mint Cockpit UI**:
  - **Dynamic Radial Speedometer**: Central gauge with digital speed numerals, motor RPM, gear capsule, dual throttle/brake micro-meters, and steering angle readout.
  - **Battery & Range Hero**: High-visibility SoC arc, pack voltage (V), current (A), and estimated range (`mi`).
  - **Bidirectional Power / Regen Bar**: Live kW delivery and regenerative braking recapture indicators.
  - **4-Wheel TPMS Monitoring Pod**: Top-down chassis schematic tracking corner tire pressures (`psi`) and temperatures (`°F`).
  - **AWD Dynamic Torque Vectoring Pod**: Real-time front and rear motor torque allocation in `lb-ft` with mode bias.
  - **Thermal Diagnostics Pod**: Continuous monitoring for motor, inverter, and battery pack temperatures (`°F`).
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
│   ├── __init__.py            # Package version (v6.1.0)
│   ├── can_bus_source.py      # CAN Bus interface, frame decoders, and synchronized mock transmitter
│   ├── simulation_source.py   # Video-game interactive EV dynamics engine (W/A/S/D, 6-speed manual, D1-D6 auto)
│   ├── telemetry_source.py    # Autonomous EV driving cycle telemetry stream (Test Mode, D1-D6 auto)
│   ├── dashboard_gui.py       # PyQt6 digital cluster interface & 800x480 auto-scaling engine
│   └── database.py            # PostgreSQL persistence: batched writer, sessions, retention, write controls, exports
├── figma-gui/                 # Authenticated Technician Web Portal (FastAPI + React 19)
│   ├── backend/               # FastAPI async REST/WebSocket engine & database adapter
│   ├── web/                   # React 19 / Vite cyber pit-wall client (Recharts traces)
│   ├── tests/                 # PostgreSQL integration tests
│   └── README.md              # Technician interface documentation
├── tests/
│   └── test_voltesse.py       # Comprehensive unit and integration test suite (33 tests)
├── main.py                    # Application lifecycle, transmission, and mode controller
├── requirements.txt           # Unified project dependencies (PyQt6, FastAPI, uvicorn, psycopg)
├── AGENTS.md                  # Embedded developer rules, architecture contracts & specifications
└── README.md                  # Project documentation
```

---

## Keyboard Controls & Hotkeys

| Key | Function | Mode Availability |
| :--- | :--- | :--- |
| `1` / `Fn 1` / `Num 1` | Switch to **Race Mode (CAN Bus)** | Global |
| `2` / `F2` / `Num 2` | Switch to **Simulation Mode (Keyboard Game)** | Global |
| `3` / `F3` / `Num 3` | Switch to **Test Mode (Autonomous Mock)** | Global |
| `Tab` | Cycle through Operating Modes (Race ➔ Sim ➔ Test) | Global |
| `T` | **Toggle Transmission (Auto ⮂ Manual)** | **Race & Sim Modes** *(Disabled in Test Mode)* |
| `E` | **Upshift** (`1` ➔ `6` in Manual, or selector in Auto) | Global |
| `C` | **Downshift** (`6` ➔ `1` ➔ `N` ➔ `R` in Manual, or selector in Auto) | Global |
| `G` | Cycle Gear (`P-R-N-D-B` in Auto, Upshift in Manual) | Global |
| `Left Arrow` | **Previous Cockpit Page (Left ◄)** | Global (Race, Sim, Test) |
| `Right Arrow` | **Next Cockpit Page (Right ►)** | Global (Race, Sim, Test) |
| `V` | **Cycle Cockpit Pages** (`Speed` ➔ `Battery` ➔ `Powertrain` ➔ `TPMS`) | Global (Race, Sim, Test) |
| `X` | **Swap Wing Views (Alternate Layout)** | Global (Race, Sim, Test) |
| `B` | **Toggle Cluster Theme** (OLED Beta ⮂ Classic) | Global (Race, Sim, Test) |
| `-` / `_` | **Zoom Out UI** (reduce cockpit scale by 5%) | Global |
| `+` / `=` | **Zoom In UI** (increase cockpit scale by 5%) | Global |
| `0` | **Reset UI Zoom** to default (100%) | Global |
| `W` / `Up Arrow` | Accelerate (Throttle ramp-up) | Simulation Mode |
| `S` / `Down Arrow` | Brake / Regenerative Deceleration | Simulation Mode |
| `A` / `Left Arrow` | Steer Left (Dynamic steering angle) | Simulation Mode |
| `D` / `Right Arrow` | Steer Right (Dynamic steering angle) | Simulation Mode |
| `M` | Cycle Drive Mode (ECO ➔ DRIVE ➔ SPORT) | Global |
| `F11` | Toggle Fullscreen / Windowed Mode | Global |
| `L` | Toggle Active Logging Stream | Global |
| `Q` / `Esc` | Graceful Exit | Global |

---

## Technician Web Portal (Voltesse Pit-Wall)

The technician portal provides real-time pit-wall telemetry monitoring, session playback, and calibration diagnostics. Run with:

```bash
cd figma-gui
python3 -m uvicorn backend.app:create_app --factory --host 0.0.0.0 --port 8501
```

- **Live Telemetry Channel**: Real-time 20 Hz push stream (`WebSocket /api/ws/telemetry`) directly from in-memory ring buffer with packet latency indicators (<15ms), 6-card primary strip, stacked synchronized Recharts traces (Speed/RPM, Driver Demand/Net Power, Motor Core Temp), and full thermal matrix (`°F`).
- **Diagnostics Channel**: High-resolution performance curves (Energy Efficiency vs. Speed, Power Draw vs. Motor Temp, Battery SoC vs. Distance, Power Draw vs. RPM, Motor Temp rise vs. Time).
- **Sessions Channel**: Historical timing-board log with session duration, peak thermals (`°F`), max speed (`MPH`), and total distance (`mi`).
- **Settings Channel**: Calibration of motor thermal warning limit (`110°F`–`230°F`, default `160°F`), low battery alert threshold (`5%`–`40%`, default `20%`), and dynamic OLED palette calibration.

---

## Embedded & Raspberry Pi Startup Services (Systemd)

Systemd unit definitions are located in `services/` for running the driver cockpit and technician portal automatically on boot (e.g. Raspberry Pi with 800×480 touchscreen):
- `services/voltesse-dash.service`: Fullscreen kiosk launcher via `cage` Wayland compositor running the PyQt6 cluster GUI.
- `services/voltesse-figma-gui.service`: FastAPI/React technician web interface running on port 8501.

### Quick Setup on Raspberry Pi:

```bash
# 1. Copy service files to systemd directory
sudo cp services/voltesse-*.service /etc/systemd/system/

# 2. Reload systemd daemon
sudo systemctl daemon-reload

# 3. Enable and start services on boot
sudo systemctl enable --now voltesse-dash.service
sudo systemctl enable --now voltesse-figma-gui.service
```

### Monitoring & Logs:

```bash
# Cockpit GUI logs
journalctl -u voltesse-dash.service -f

# Technician Portal logs
journalctl -u voltesse-figma-gui.service -f
```

---

## Running Tests

Execute the automated test suites with Python's built-in `unittest` (33 total tests):

```bash
# Run cockpit unit and integration tests (33 tests)
python -m unittest discover tests
```

---

## License

MIT License. Designed and engineered for high-performance EV telemetry systems.
