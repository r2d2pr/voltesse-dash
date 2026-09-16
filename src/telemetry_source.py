"""
Voltesse Dash - Mock Telemetry Stream
Asynchronous telemetry generator with realistic EV powertrain dynamics simulation.
Runs on a dedicated QThread to prevent any blocking of the GUI main thread.
"""

import math
import random
import time
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.database import TelemetryRecord


class MockTelemetryStream(QThread):
    """
    Simulates real-time EV telemetry data asynchronously.
    Emits TelemetryRecord objects over Qt signals at a specified frequency.
    """

    # Signal emitted on every new telemetry packet
    telemetry_received = pyqtSignal(TelemetryRecord)
    status_changed = pyqtSignal(str)

    # Simulation modes
    MODES = ["ECO", "DRIVE", "SPORT"]

    def __init__(
        self,
        update_interval_ms: int = 50,  # 20 Hz
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.update_interval_ms = update_interval_ms
        self._running = False
        self._paused = False

        # Vehicle State Variables
        self.speed_kmh = 0.0
        self.target_speed = 0.0
        self.motor_rpm = 0
        self.battery_soc = 88.5  # %
        self.battery_voltage = 398.4  # V
        self.battery_current = 0.0  # A
        self.battery_power_kw = 0.0  # kW
        self.battery_temp_c = 29.5  # °C
        self.motor_temp_c = 36.2  # °C
        self.inverter_temp_c = 33.8  # °C
        self.throttle_pct = 0.0  # %
        self.brake_pct = 0.0  # %
        self.drive_mode = "DRIVE"
        self.trip_distance_km = 0.0

        # State machine for dynamic driving cycle simulation
        self._sim_state = "ACCELERATING"
        self._state_timer = 0.0
        self._state_duration = 5.0
        self._cycle_time = 0.0
        self._last_tick = time.time()

    def run(self) -> None:
        """Main QThread execution loop."""
        self._running = True
        self._last_tick = time.time()
        self.status_changed.emit("RUNNING")

        while self._running:
            if not self._paused:
                now = time.time()
                dt = max(0.001, min(0.2, now - self._last_tick))
                self._last_tick = now

                self._step_simulation(dt)
                record = self._build_record()
                self.telemetry_received.emit(record)
            else:
                self._last_tick = time.time()

            self.msleep(self.update_interval_ms)

        self.status_changed.emit("STOPPED")

    def stop(self) -> None:
        """Gracefully stop the background telemetry thread."""
        self._running = False
        self.wait(2000)

    def toggle_pause(self) -> bool:
        """Pause or resume telemetry generation."""
        self._paused = not self._paused
        self.status_changed.emit("PAUSED" if self._paused else "RUNNING")
        return self._paused

    def set_drive_mode(self, mode: str) -> None:
        """Manually select drive mode (ECO, DRIVE, SPORT)."""
        if mode in self.MODES:
            self.drive_mode = mode

    def cycle_drive_mode(self) -> str:
        """Cycles through drive modes."""
        curr_idx = self.MODES.index(self.drive_mode)
        next_idx = (curr_idx + 1) % len(self.MODES)
        self.drive_mode = self.MODES[next_idx]
        return self.drive_mode

    def _step_simulation(self, dt: float) -> None:
        """Simulates physical EV dynamics for elapsed time dt."""
        self._cycle_time += dt
        self._state_timer += dt

        # State transition logic
        if self._state_timer >= self._state_duration:
            self._state_timer = 0.0
            self._transition_state()

        # Update throttle / brake based on state
        if self._sim_state == "ACCELERATING":
            target_throttle = 65.0 if self.drive_mode != "SPORT" else 92.0
            target_brake = 0.0
            max_spd = 95.0 if self.drive_mode == "ECO" else 135.0
            self.target_speed = min(max_spd, self.target_speed + 25.0 * dt)
        elif self._sim_state == "HARD_ACCEL":
            target_throttle = 98.0
            target_brake = 0.0
            self.target_speed = 155.0
        elif self._sim_state == "CRUISING":
            target_throttle = 18.0 + 3.0 * math.sin(self._cycle_time * 0.8)
            target_brake = 0.0
            self.target_speed = 75.0 + 10.0 * math.sin(self._cycle_time * 0.4)
        elif self._sim_state == "REGEN_BRAKING":
            target_throttle = 0.0
            target_brake = 45.0
            self.target_speed = max(0.0, self.target_speed - 35.0 * dt)
        elif self._sim_state == "COASTING":
            target_throttle = 0.0
            target_brake = 0.0
            self.target_speed = max(0.0, self.target_speed - 8.0 * dt)
        elif self._sim_state == "STOPPED":
            target_throttle = 0.0
            target_brake = 15.0
            self.target_speed = 0.0
        else:
            target_throttle = 10.0
            target_brake = 0.0

        # Smooth throttle / brake response
        smooth_rate = 6.0 * dt
        self.throttle_pct += (target_throttle - self.throttle_pct) * min(1.0, smooth_rate)
        self.brake_pct += (target_brake - self.brake_pct) * min(1.0, smooth_rate)

        # Speed dynamics
        accel_multiplier = 1.3 if self.drive_mode == "SPORT" else (0.8 if self.drive_mode == "ECO" else 1.0)
        drive_force = (self.throttle_pct / 100.0) * 45.0 * accel_multiplier
        brake_force = (self.brake_pct / 100.0) * 60.0
        drag_force = 0.0008 * (self.speed_kmh ** 2) + 0.5

        net_accel = drive_force - brake_force - drag_force
        self.speed_kmh = max(0.0, self.speed_kmh + net_accel * dt)

        # Motor RPM calculation (assuming 8.5:1 reduction gear ratio and ~0.55m wheel)
        rpm_factor = 78.5
        self.motor_rpm = int(self.speed_kmh * rpm_factor + random.uniform(-15, 15))
        if self.speed_kmh < 0.5:
            self.motor_rpm = 0

        # Current & Power calculations
        if self.throttle_pct > 2.0:
            # Drawing power from battery (discharge)
            base_draw = (self.throttle_pct / 100.0) * 260.0 * accel_multiplier
            self.battery_current = base_draw + random.uniform(-1.5, 1.5)
        elif self.brake_pct > 2.0 and self.speed_kmh > 5.0:
            # Regenerative braking (recharging battery)
            regen_max = -75.0 if self.drive_mode != "ECO" else -95.0
            self.battery_current = (self.brake_pct / 100.0) * regen_max + random.uniform(-1.0, 1.0)
        else:
            # Idle / auxiliary electronics draw (HVAC, pumps, Dash)
            self.battery_current = 2.4 + random.uniform(-0.3, 0.3)

        # Voltage sag under load
        nominal_pack_v = 400.0
        internal_resistance = 0.045  # Ohms
        soc_factor = (self.battery_soc / 100.0) * 25.0  # Voltage drops as SoC drops
        self.battery_voltage = (nominal_pack_v - 25.0 + soc_factor) - (self.battery_current * internal_resistance)

        # Instantaneous Power (kW)
        self.battery_power_kw = (self.battery_voltage * self.battery_current) / 1000.0

        # SoC Depletion / Regen Integration
        # Energy = Power * dt hours
        energy_kwh = (self.battery_power_kw * (dt / 3600.0))
        pack_capacity_kwh = 60.0  # 60 kWh pack
        soc_delta = (energy_kwh / pack_capacity_kwh) * 100.0
        self.battery_soc = max(1.0, min(100.0, self.battery_soc - soc_delta))

        # Thermal dynamics (gradual thermal inertia)
        ambient_temp = 24.0
        # Inverter heats with current magnitude
        inverter_heat = (abs(self.battery_current) / 250.0) ** 1.8 * 8.0 * dt
        inverter_cool = (self.inverter_temp_c - ambient_temp) * 0.015 * dt
        self.inverter_temp_c = max(ambient_temp, self.inverter_temp_c + inverter_heat - inverter_cool)

        # Motor heats with RPM & torque
        motor_heat = ((self.motor_rpm / 9000.0) * 3.0 + (self.throttle_pct / 100.0) * 6.0) * dt
        motor_cool = (self.motor_temp_c - ambient_temp) * 0.02 * (1.0 + self.speed_kmh / 60.0) * dt
        self.motor_temp_c = max(ambient_temp, self.motor_temp_c + motor_heat - motor_cool)

        # Battery temp changes slowly
        batt_heat = ((abs(self.battery_current) / 200.0) ** 2) * 1.5 * dt
        batt_cool = (self.battery_temp_c - ambient_temp) * 0.005 * dt
        self.battery_temp_c = max(ambient_temp, self.battery_temp_c + batt_heat - batt_cool)

        # Distance calculation
        dist_delta_km = (self.speed_kmh * dt) / 3600.0
        self.trip_distance_km += dist_delta_km

    def _transition_state(self) -> None:
        """Cycle through realistic drive phases."""
        states = ["ACCELERATING", "CRUISING", "HARD_ACCEL", "COASTING", "REGEN_BRAKING", "STOPPED"]
        weights = [0.30, 0.30, 0.10, 0.12, 0.13, 0.05]

        # Prevent stopping if we just stopped
        if self._sim_state == "STOPPED":
            self._sim_state = "ACCELERATING"
            self._state_duration = random.uniform(5.0, 9.0)
        elif self.speed_kmh > 120.0:
            self._sim_state = random.choice(["CRUISING", "REGEN_BRAKING", "COASTING"])
            self._state_duration = random.uniform(3.0, 6.0)
        else:
            self._sim_state = random.choices(states, weights=weights)[0]
            self._state_duration = random.uniform(3.5, 8.0)

    def _build_record(self) -> TelemetryRecord:
        """Assembles a TelemetryRecord dataclass with simulated sensor metrics and alerts."""
        warnings: List[str] = []
        if self.battery_soc < 15.0:
            warnings.append("LOW BATTERY")
        if self.battery_temp_c > 45.0 or self.motor_temp_c > 85.0 or self.inverter_temp_c > 75.0:
            warnings.append("THERMAL WARNING")
        if self.speed_kmh > 140.0:
            warnings.append("HIGH SPEED")
        if self.battery_current < -65.0:
            warnings.append("HIGH REGEN")

        return TelemetryRecord(
            timestamp=time.time(),
            speed_kmh=round(self.speed_kmh, 1),
            motor_rpm=self.motor_rpm,
            battery_soc=round(self.battery_soc, 1),
            battery_voltage=round(self.battery_voltage, 1),
            battery_current=round(self.battery_current, 1),
            battery_power_kw=round(self.battery_power_kw, 1),
            battery_temp_c=round(self.battery_temp_c, 1),
            motor_temp_c=round(self.motor_temp_c, 1),
            inverter_temp_c=round(self.inverter_temp_c, 1),
            throttle_pct=round(self.throttle_pct, 1),
            brake_pct=round(self.brake_pct, 1),
            drive_mode=self.drive_mode,
            trip_distance_km=round(self.trip_distance_km, 2),
            warnings=warnings,
        )
