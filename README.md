# Voltesse Dash ⚡ v5.4.0

[![Version](https://img.shields.io/badge/version-5.4.0-00F5A0.svg)](https://github.com/r2d2pr/voltesse-dash)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/PyQt-6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Web](https://img.shields.io/badge/Streamlit-1.66-red.svg)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![CAN](https://img.shields.io/badge/CAN-SocketCAN%20%7C%20virtual-orange.svg)](https://python-can.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern automotive digital cockpit, web-based technician admin portal, and local telemetry logging engine for embedded displays, including Raspberry Pi, and EV powertrains. Version 5.4.0 introduces the **Dynamic Ambient Theme & Accent Palette Engine** with 5 signature OLED colorways, hotkey `P` cycling, centered glassmorphic speedometer toast overlay, technician portal calibration swatches, and `--palette` CLI support. Built with **Python**, **PyQt6**, **Streamlit**, **python-can**, and **PostgreSQL**.

---

## What's New in Version 5.4.0 🚀

- 🎨 **Dynamic Ambient Theme & Accent Palette Engine**:
  - Engineered 5 signature automotive-grade OLED colorways tailored for pure black void (`#000000`):
    - **`CYBER_MINT`** (`mint`, default): Voltesse signature cybernetic electric neon (`#00F5A0` primary, `#5CFFC7` highlight, `#00E5FF` secondary).
    - **`STEALTH_MONOCHROME`** (`stealth`): Pure hypercar titanium silver & white (`#E2E8F0` primary, `#FFFFFF` highlight, `#94A3B8` secondary).
    - **`SOLAR_AMBER`** (`amber`): Endurance motorsport amber tachometer (`#FFB800` primary, `#FFD166` highlight, `#FF9F1C` secondary).
    - **`TRACK_REDLINE`** (`redline`): Aggressive track attack crimson (`#FF3366` primary, `#FF6B8B` highlight, `#FF9900` secondary).
    - **`NEON_SYNTHWAVE`** (`synthwave`): Cyberpunk night drive magenta & cyan (`#D946EF` primary, `#F472B6` highlight, `#06B6D4` secondary).
  - **Hotkey `P` & Auto-Switch UX**: Pressing `P` cycles between palettes in sequence (`mint` ➔ `stealth` ➔ `amber` ➔ `redline` ➔ `synthwave` ➔ loop). If pressed in Classic mode, the cluster automatically switches to OLED mode and activates the next palette.
  - **Centered Glassmorphic Speedometer Toast**: Switching palettes triggers an animated floating glassmorphic pill directly across the center dial (`🎨 PALETTE: [NAME]`) with a smooth 1.5-second cubic fade out and top HUD ribbon status badge.
  - **Coordinated Cockpit Styling Across All Pages**: The illuminated binnacle cowl, dial halos, battery SoC arc, powertrain torque split bars, TPMS chassis wireframe, and compact speed pod accent seam all dynamically adapt to the active palette.
  - **Strict ISO/SAE Safety Invariant Lock**: Tachometer redline (7–8k RPM), brake pedal indicators, and critical thermal/pressure warnings remain invariant in standardized Coral Red (`#FF4D6D`) and Amber (`#FFB800`).
  - **Technician Pit-Wall Calibration Preview**: Settings channel in the Streamlit portal features interactive swatch cards, live hex/RGB breakdown, contrast metrics, and an SVG/CSS cluster speedometer simulation preview.
  - **CLI Argument Support**: Launch directly into any colorway via `--palette [mint|stealth|amber|redline|synthwave]`.
- 🧪 **Automated Test Suite Verification**:
  - 47 unit tests passing with 100% green status (33 cockpit GUI tests + 14 technician portal tests).

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
│   ├── __init__.py            # Package version (v5.4.0)
│   ├── can_bus_source.py      # CAN Bus interface, frame decoders, and synchronized mock transmitter
│   ├── simulation_source.py   # Video-game interactive EV dynamics engine (W/A/S/D, 6-speed manual, D1-D6 auto)
│   ├── telemetry_source.py    # Autonomous EV driving cycle telemetry stream (Test Mode, D1-D6 auto)
│   ├── dashboard_gui.py       # PyQt6 digital cluster interface & 800x480 auto-scaling engine
│   └── database.py            # PostgreSQL persistence: batched writer, sessions, retention, write controls, exports
├── technician-gui/            # Voltesse Pit-Wall Streamlit web interface
│   ├── app.py                 # Streamlit entrypoint and navigation controller
│   ├── data/
│   │   ├── db.py              # PostgreSQL database queries, authentication & real-time telemetry feed
│   │   └── simulator.py       # Deterministic fallback simulator for bench testing
│   ├── ui/                    # Modular UI pages (Live, Diagnostics, Sessions, Settings, Login)
│   ├── tests/                 # Unit tests for database integration and simulator
│   └── requirements.txt       # Streamlit dependencies (streamlit, pandas, plotly, psycopg)
├── tests/
│   └── test_voltesse.py       # Comprehensive unit and integration test suite (33 tests)
├── main.py                    # Application lifecycle, transmission, and mode controller
├── requirements.txt           # Driver cockpit dependencies (PyQt6, python-can, psycopg)
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

The technician portal provides pit-wall telemetry monitoring, session playback, and calibration diagnostics. Run with:

```bash
streamlit run technician-gui/app.py
```

- **Live Telemetry Channel**: Real-time 1-second auto-streaming (`@st.fragment`) telemetry from PostgreSQL with link status (`ACTIVE`, `STANDBY`, `DISCONNECTED`), packet latency indicators, 6-card primary strip, stutter-free synchronized traces, and full thermal matrix (`°F`).
- **Diagnostics Channel**: High-resolution performance curves (Energy Efficiency vs. Speed, Power Draw vs. Motor Temp, Battery SoC vs. Distance, Power Draw vs. RPM, Motor Temp rise vs. Time).
- **Sessions Channel**: Historical timing-board log with session duration, peak thermals (`°F`), max speed (`MPH`), and total distance (`mi`).
- **Settings Channel**: Calibration of motor thermal warning limit (`110°F`–`230°F`, default `160°F`), low battery alert threshold (`5%`–`40%`, default `20%`), and database link diagnostics.

---

## Running Tests

Execute the automated test suites with Python's built-in `unittest` (46 total tests):

```bash
# Run cockpit unit and integration tests (32 tests)
python -m unittest discover tests

# Run technician web app database and simulation tests (14 tests)
python -m unittest discover technician-gui/tests
```

---

## License

MIT License. Designed and engineered for high-performance EV telemetry systems.
