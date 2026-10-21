# Voltesse Dash — Agentic Development & Architecture Guidelines (GEMINI.md)

Welcome to **Voltesse Dash** ⚡. This document defines the engineering standards, architectural contracts, design aesthetics, testing protocols, and release workflows required to build and maintain the Voltesse digital cockpit, telemetry engine, and technician tools.

---

## 1. Project Vision & Architecture

Voltesse Dash is a production-grade, distraction-free automotive digital instrument cluster, local telemetry persistence engine, and technician portal designed for electric vehicles (EVs) and embedded cluster panels (including Raspberry Pi 800×480 touchscreens, automotive HUDs, and high-resolution digital displays up to 4K).

### Core Technology Stack
- **Cluster GUI**: Python 3.10+, **PyQt6** (custom automotive vector rendering with `QPainter`, hardware-composited geometry animations, zero QML/web-view overhead for guaranteed 60 FPS performance).
- **Vehicle Bus Interface**: **python-can** with `SocketCAN` support on Linux/RPi, virtual CAN bus, and synchronized frame decoders.
- **Persistence Engine**: **PostgreSQL 16** with asynchronous, micro-batched worker threads preventing flash wear on SD cards.
- **Technician Portal**: **Streamlit** multi-page admin dashboard for bench calibration, session export, and diagnostics.
- **Operating Modes**:
  1. 🏎️ **Race Mode (Default)**: Direct CAN bus frame decoding for live vehicle telemetry.
  2. 🎮 **Simulation Mode**: Real-time video game physics engine mapped to keyboard inputs (`W/A/S/D`, arrow keys, shifting).
  3. 🧪 **Test Mode**: Autonomous canned EV driving cycles for bench testing.

---

## 2. Hard Architectural Rules & Non-Negotiable Constraints

### 🇺🇸 Imperial Units Exclusively (Metric Deprecated)
- All driver-facing telemetry, gauges, readouts, and database persistence are strictly locked to the **Imperial System**:
  - **Speed**: `MPH` (0–120 dial and digital numerals).
  - **Distance**: Miles (`mi`) for trip odometer and battery range.
  - **Thermals**: Degrees Fahrenheit (`°F`) for motor, inverter, battery pack, and tire thermals.
  - **Tire Pressure (TPMS)**: Pounds per square inch (`psi`).
  - **Dual-Motor Torque Vectoring**: Foot-pounds (`lb-ft`).
  - **Energy Consumption**: `kWh/100mi`.
- **Constraint**: Never reintroduce metric units, metric toggle badges, or unit switching toggles back to the cluster GUI.

### 🔴 Continuous Always-Active Logging
- The telemetry engine logs continuously to PostgreSQL throughout operation.
- Logging cannot be silently disabled during vehicle operation. The legacy `L` toggle is retained as a signal stub, but telemetry capture remains active for driver safety and diagnostic integrity.

### ⚡ Instant Frame-1 Display Initialization
- The cockpit window (`VoltesseDashboard`) must display immediately on Frame 1 before attempting network handshakes, CAN socket initialization, or database connects. This prevents black-screen timeouts under embedded Wayland/Cage kiosk compositors.

### 🪟 Streamlined, Non-Invasive Top HUD Ribbon
- Minimalist translucent cyber-ribbon (`rgba(4, 12, 8, 0.65)` with cyber-mint border).
- Free from redundant clutter:
  - **Left**: Left Turn Signal (`◄`), Brand (`⚡ VOLTESSE`), and compact Speed Fallback badge (`65 MPH [D4]`).
  - **Center**: Interactive Page Navigator (`◄ SPEED [1/4] ►`) and dynamic active warning alerts.
  - **Right**: Drive Mode (`SPORT` / `DRIVE` / `ECO`), Ambient Temperature (`72°F`), 12-Hour AM/PM Clock with seconds, Right Turn Signal (`►`).

### 🎬 Animated View Transitions (`AnimatedStackedWidget`)
- Central cockpit views must transition via `AnimatedStackedWidget` with smooth directional sliding and depth crossfade:
  - **Right Navigation** (`►`, `Right Arrow`, `V` key): Current view slides left, new view slides in from right.
  - **Left Navigation** (`◄`, `Left Arrow`): Current view slides right, new view slides in from left.
  - **Snappy Easing**: 260ms duration with `QEasingCurve.Type.OutCubic`.
  - **Zero Ongoing Overhead**: Always purge graphics effects on completion (`widget.setGraphicsEffect(None)`).
  - **Immediate Interruption Settlement**: Rapid inputs must call `finish_animation()` to immediately settle the in-flight view and transition to the target page without stutter or ghosting.
  - **Tactile Chevrons**: Nav frame chevrons (`◄` / `►`) flash white briefly upon click/press. Single-shot timers MUST pass the button context object (`QTimer.singleShot(150, btn, callback)`) to prevent callbacks on deleted C++ pointers.

### ⚡ Always-Visible Speed Pod on Non-Speed Pages
- When navigated away from Page 0 (`SPEED`) to Page 1 (`BATTERY`), Page 2 (`POWERTRAIN`), or Page 3 (`TPMS`), an integrated `CompactSpeedPod` MUST remain permanently visible.
- Displays: Speed (`MPH`), dynamic cyan-to-mint speed bar, RPM, transmission mode & dynamic gear pill (e.g. `AUTO [4]`, `MANUAL [5]`), and micro-indicators for throttle (`THR %`), brake (`BRK %`), and steering (`STR °`).
- **Wing Swapping (`X` key / `--swap-wings`)**: Positions of the compact speed pod and the hero diagnostic widget can be dynamically swapped left ⮂ right.

### 💎 Translucent Obsidian Cyber-Dock (Bottom Telemetry Deck)
- Pinned constant bottom bar (`rgba(4, 14, 10, 0.75)` with top cyber-mint accent line).
- **Sculpted Thermal Cards**:
  - Dedicated cards for **⚡ MOTOR**, **⚡ INV**, and **🔋 BATT**.
  - **State-Aware Glowing Borders & Status Tags**:
    - Nominal: Mint glow with `OK` tag (< 160°F / 140°F / 120°F).
    - Warm: Amber glow with `WARM` tag (≥ 160°F / 140°F / 120°F).
    - Hot: Neon red glow & alert styling with `HOT` tag (≥ 195°F / 175°F / 140°F).
  - **Micro-Thermometer Progress Fill Bars**: Sub-millimeter visual level indicators relative to thermal limits.
- **Trip Odometer Pod**: Distinct card with glowing `📍 TRIP` icon and high-contrast Consolas mileage (`mi`).

---

## 3. Transmission & Vehicle Dynamics Specification

### Automatic Transmission (Auto PRNDB with D1–D6)
- Active gear ratios are dynamically calculated from vehicle velocity:
  - `D1`: 0 – 16 mph
  - `D2`: 16 – 31 mph
  - `D3`: 31 – 48 mph
  - `D4`: 48 – 68 mph
  - `D5`: 68 – 90 mph
  - `D6`: 90+ mph
- Speedometer gear capsule displays active ratio: `[P] [R] [N] [D3] [B]`.

### Sequential Manual Transmission
- 6-Speed sequential shifting: `R ⮂ N ⮂ 1 ⮂ 2 ⮂ 3 ⮂ 4 ⮂ 5 ⮂ 6`.
- Hotkey `T` toggles Auto ⮂ Manual in Race and Sim modes.
- **Test Mode Lock**: Test mode is strictly locked to Automatic transmission; attempting to toggle shows an on-screen warning: `⚠️ TEST MODE: AUTO ONLY`.

---

## 4. Coding & Automotive UI Best Practices

1. **Cyber-Mint Color Palette**:
   - `COLOR_MINT = #00F5A0` (Primary Neon Mint)
   - `COLOR_MINT_BRIGHT = #5CFFC7` (Highlight Mint)
   - `COLOR_CYAN = #00E5FF` (Simulation Cyan)
   - `COLOR_AMBER = #FFB800` (Thermal Warning Amber)
   - `COLOR_RED = #FF4D6D` (Critical / Brake Red)
   - `COLOR_BG_DARK = #030706` (Obsidian Cockpit Void)
2. **Dynamic Scaling & Proportions**:
   - Every custom widget must adapt cleanly in its `paintEvent` using proportional coordinates (`min(w, h)` scaling).
   - Reserve sufficient horizontal and vertical padding for text labels to prevent clipping on 800×480 displays (e.g. range `231 mi`, trip `28.46 mi`, sensor labels).
3. **No Unhandled Qt Exceptions**:
   - Guard against `NoneType` or null painter references.
   - Always call `painter.end()` at the end of custom paint events.
   - Never use long-running synchronous sleeps on the GUI thread; use `QTimer` or worker `QThread`s.

---

## 5. Testing & Verification Requirements

- **Local Python Environment**: `.\.venv\Scripts\python.exe`
- **Unit Test Discovery**:
  ```powershell
  .\.venv\Scripts\python.exe -m unittest discover -s tests -v
  ```
- **Requirements for PRs / Changes**:
  - **100% Green**: All tests in `tests/test_voltesse.py` must pass with zero failures or errors.
  - **Preserve Existing Attributes**: Do NOT break legacy or test-inspected attributes on `VoltesseDashboard` (`page_stack`, `center_stack`, `speed_gauge`, `battery_hero`, `powertrain_hero`, `tpms_widget`, `compact_speed_widget`, `compact_speed_pods`, `trip_pod`, `thermal_widget`, `bottom_bar`).
  - **QTimer & Thread Safety**: Always supply a context QObject when scheduling single-shot timers to prevent dangling callbacks on destructed widgets.

---

## 6. Release & Git Workflow Protocol

1. **Version Synchronization**:
   - Update `__version__ = "X.Y.Z"` in `src/__init__.py`.
   - Update version badges, title, and "What's New in Version X.Y.Z" in `README.md`.
   - Update test count in `README.md` if new tests were added.
2. **Clean Working Tree**:
   - Delete temporary render scripts, scratch test files, and artifacts before staging.
3. **Git Tagging Standard (STRICT)**:
   - **Single Tag with `v` Prefix ONLY**: Always create annotated tags formatted as `vX.Y.Z` (e.g. `v4.3.0`).
   - **NEVER Push Duplicate Un-Prefixed Tags**: Do NOT create or push tags like `4.3.0` alongside `v4.3.0`.
   - Push command:
     ```powershell
     & "C:\Program Files\Git\cmd\git.exe" push origin main --tags
     ```
