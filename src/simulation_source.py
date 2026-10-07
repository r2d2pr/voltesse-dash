"""
Voltesse Dash - Interactive Video-Game Telemetry Simulation Stream
Simulates an authentic EV driving experience controllable via keyboard:
- Throttle (W / Up Arrow)
- Friction Brake & Regenerative Braking (S / Down Arrow)
- Steering Wheel with dynamic centering spring (A/D, Left/Right Arrows)
- Automatic Transmission (PRNDB with dynamic speed-based gear display D1-D6)
- 6-Speed Sequential Manual Transmission (R, N, 1-6) with rev-limiter and realistic gear ratios
- Drive Modes (ECO, DRIVE, SPORT) affecting torque delivery, top speed, and regen
"""

import math
import random
import threading
import time
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.database import TelemetryRecord


class SimulationTelemetryStream(QThread):
    """
    QThread running an interactive real-time EV driving physics simulation
    with keyboard-controlled dynamics and full Auto/Manual transmission support.
    """

    telemetry_received = pyqtSignal(TelemetryRecord)
    status_changed = pyqtSignal(str)

    MODES = ["DRIVE", "SPORT", "ECO"]
    GEARS_AUTO = ["P", "R", "N", "D", "B"]
    GEARS_MANUAL = ["R", "N", "1", "2", "3", "4", "5", "6"]

    # Gear ratios for manual transmission and auto gear simulation
    GEAR_RATIOS = {
        "R": 1.20,
        "N": 0.0,
        "1": 1.25,
        "2": 0.65,
        "3": 0.45,
        "4": 0.32,
        "5": 0.24,
        "6": 0.18,
    }
    GEAR_MAX_SPEEDS = {
        "R": 35.0,
        "N": 0.0,
        "1": 48.0,
        "2": 80.0,
        "3": 118.0,
        "4": 155.0,
        "5": 188.0,
        "6": 220.0,
    }

    @staticmethod
    def get_auto_gear_for_speed(speed_kmh: float) -> int:
        """Determines active automatic gear ratio based on vehicle velocity."""
        if speed_kmh < 25.0:
            return 1
        elif speed_kmh < 50.0:
            return 2
        elif speed_kmh < 78.0:
            return 3
        elif speed_kmh < 110.0:
            return 4
        elif speed_kmh < 145.0:
            return 5
        else:
            return 6

    def __init__(
        self,
        update_interval_ms: int = 40,  # 25 Hz
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.update_interval_ms = update_interval_ms
        self._running = False
        self._paused = False
        self._input_lock = threading.Lock()

        # Keyboard Control Flags
        self._key_throttle = False
        self._key_brake = False
        self._key_steer_left = False
        self._key_steer_right = False

        # Transmission State
        self.transmission_mode = "AUTO"  # "AUTO" or "MANUAL"
        self.current_gear = "D1"         # e.g. D1-D6, P, R, N, B in Auto; 1-6, N, R in Manual

        # Vehicle State Variables
        self.speed_kmh = 0.0
        self.motor_rpm = 0
        self.battery_soc = 88.5
        self.battery_voltage = 398.0
        self.battery_current = 0.0
        self.battery_power_kw = 0.0
        self.battery_temp_c = 29.5
        self.motor_temp_c = 36.0
        self.inverter_temp_c = 33.5
        self.throttle_pct = 0.0
        self.brake_pct = 0.0
        self.steering_angle = 0.0  # degrees: -45 to +45
        self.drive_mode = "DRIVE"
        self.trip_distance_km = 0.0

        self._last_tick = time.time()

    def set_inputs(
        self,
        throttle: bool,
        brake: bool,
        steer_left: bool,
        steer_right: bool,
    ) -> None:
        """Thread-safe update of keyboard driving controls."""
        with self._input_lock:
            self._key_throttle = throttle
            self._key_brake = brake
            self._key_steer_left = steer_left
            self._key_steer_right = steer_right

    def cycle_drive_mode(self) -> str:
        """Cycles through ECO, DRIVE, and SPORT."""
        curr_idx = self.MODES.index(self.drive_mode)
        next_idx = (curr_idx + 1) % len(self.MODES)
        self.drive_mode = self.MODES[next_idx]
        return self.drive_mode

    def toggle_transmission_mode(self) -> str:
        """Toggles between AUTO and MANUAL transmission modes."""
        with self._input_lock:
            if self.transmission_mode == "AUTO":
                self.transmission_mode = "MANUAL"
                # Pick sensible manual gear based on current speed
                self.current_gear = str(self.get_auto_gear_for_speed(self.speed_kmh))
            else:
                self.transmission_mode = "AUTO"
                if self.current_gear in ("P", "R", "N", "B"):
                    pass
                else:
                    self.current_gear = f"D{self.get_auto_gear_for_speed(self.speed_kmh)}"
        return self.transmission_mode

    def shift_up(self) -> str:
        """Upshifts gear in manual mode, or advances selector in auto mode."""
        with self._input_lock:
            if self.transmission_mode == "MANUAL":
                curr_idx = self.GEARS_MANUAL.index(self.current_gear) if self.current_gear in self.GEARS_MANUAL else 1
                if curr_idx < len(self.GEARS_MANUAL) - 1:
                    self.current_gear = self.GEARS_MANUAL[curr_idx + 1]
            else:
                base_g = self.current_gear[0] if self.current_gear else "D"
                curr_idx = self.GEARS_AUTO.index(base_g) if base_g in self.GEARS_AUTO else 3
                if curr_idx < len(self.GEARS_AUTO) - 1:
                    next_g = self.GEARS_AUTO[curr_idx + 1]
                    self.current_gear = f"D{self.get_auto_gear_for_speed(self.speed_kmh)}" if next_g == "D" else next_g
        return self.current_gear

    def shift_down(self) -> str:
        """Downshifts gear in manual mode, or reverses selector in auto mode."""
        with self._input_lock:
            if self.transmission_mode == "MANUAL":
                curr_idx = self.GEARS_MANUAL.index(self.current_gear) if self.current_gear in self.GEARS_MANUAL else 1
                if curr_idx > 0:
                    self.current_gear = self.GEARS_MANUAL[curr_idx - 1]
            else:
                base_g = self.current_gear[0] if self.current_gear else "D"
                curr_idx = self.GEARS_AUTO.index(base_g) if base_g in self.GEARS_AUTO else 3
                if curr_idx > 0:
                    prev_g = self.GEARS_AUTO[curr_idx - 1]
                    self.current_gear = f"D{self.get_auto_gear_for_speed(self.speed_kmh)}" if prev_g == "D" else prev_g
        return self.current_gear

    def shift_gear(self, gear: Optional[str] = None) -> str:
        """Shifts or cycles gear."""
        with self._input_lock:
            if gear:
                self.current_gear = gear
                return self.current_gear
            if self.transmission_mode == "MANUAL":
                return self.shift_up()
            else:
                base_g = self.current_gear[0] if self.current_gear else "D"
                curr_idx = self.GEARS_AUTO.index(base_g) if base_g in self.GEARS_AUTO else 3
                next_g = self.GEARS_AUTO[(curr_idx + 1) % len(self.GEARS_AUTO)]
                if next_g == "D":
                    self.current_gear = f"D{self.get_auto_gear_for_speed(self.speed_kmh)}"
                else:
                    self.current_gear = next_g
                return self.current_gear

    def run(self) -> None:
        """Simulation physics loop."""
        self._running = True
        self._last_tick = time.time()
        self.status_changed.emit("SIM RUNNING")

        while self._running:
            now = time.time()
            dt = max(0.001, min(0.1, now - self._last_tick))
            self._last_tick = now

            if not self._paused:
                with self._input_lock:
                    k_thr = self._key_throttle
                    k_brk = self._key_brake
                    k_left = self._key_steer_left
                    k_right = self._key_steer_right

                self._step_game_physics(dt, k_thr, k_brk, k_left, k_right)
                rec = self._build_record()
                self.telemetry_received.emit(rec)

            self.msleep(self.update_interval_ms)

        self.status_changed.emit("SIM STOPPED")

    def stop(self) -> None:
        """Gracefully stops the simulation."""
        self._running = False
        self.wait(2000)

    def toggle_pause(self) -> bool:
        self._paused = not self._paused
        self.status_changed.emit("SIM PAUSED" if self._paused else "SIM RUNNING")
        return self._paused

    def _step_game_physics(
        self,
        dt: float,
        k_thr: bool,
        k_brk: bool,
        k_left: bool,
        k_right: bool,
    ) -> None:
        """Realistic video game driving physics step with auto/manual dynamics."""
        # 1. Throttle response
        can_drive = True
        if self.transmission_mode == "AUTO":
            can_drive = self.current_gear.startswith("D") or self.current_gear in ("B", "R")
        else:
            can_drive = self.current_gear not in ("N", "P")

        if k_thr and can_drive:
            rate = 140.0 * dt  # Ramps up in ~0.7s
            self.throttle_pct = min(100.0, self.throttle_pct + rate)
        elif k_thr and not can_drive:
            # Free revving in Neutral
            rate = 180.0 * dt
            self.throttle_pct = min(100.0, self.throttle_pct + rate)
        else:
            fall_rate = 220.0 * dt
            self.throttle_pct = max(0.0, self.throttle_pct - fall_rate)

        # 2. Brake response
        if k_brk:
            rate = 180.0 * dt
            self.brake_pct = min(100.0, self.brake_pct + rate)
        else:
            fall_rate = 260.0 * dt
            self.brake_pct = max(0.0, self.brake_pct - fall_rate)

        # 3. Steering wheel dynamics (smooth steering + auto-centering)
        steer_speed = 90.0 * dt
        target_steer = 0.0
        if k_left and not k_right:
            target_steer = -40.0
        elif k_right and not k_left:
            target_steer = 40.0

        if target_steer != 0.0:
            if self.steering_angle < target_steer:
                self.steering_angle = min(target_steer, self.steering_angle + steer_speed)
            else:
                self.steering_angle = max(target_steer, self.steering_angle - steer_speed)
        else:
            center_speed = 110.0 * dt
            if abs(self.steering_angle) <= center_speed:
                self.steering_angle = 0.0
            elif self.steering_angle > 0:
                self.steering_angle -= center_speed
            else:
                self.steering_angle += center_speed

        # 4. Transmission & Powertrain Forces
        mode_mult = 1.35 if self.drive_mode == "SPORT" else (0.80 if self.drive_mode == "ECO" else 1.0)

        if self.transmission_mode == "MANUAL":
            ratio = self.GEAR_RATIOS.get(self.current_gear, 0.0)
            max_gear_spd = self.GEAR_MAX_SPEEDS.get(self.current_gear, 0.0)

            if self.current_gear == "N":
                drive_force = 0.0
                # Engine/motor rev in Neutral
                self.motor_rpm = int((self.throttle_pct / 100.0) * 7200.0 + random.uniform(-20, 20))
            elif self.current_gear == "R":
                drive_force = -(self.throttle_pct / 100.0) * 32.0 * mode_mult
                if abs(self.speed_kmh) > max_gear_spd:
                    drive_force = 0.0
                self.motor_rpm = int(abs(self.speed_kmh) * 120.0 + random.uniform(-10, 10))
            else:
                # Gears 1 to 6
                gear_torque_mult = (1.0 / max(0.15, ratio)) * 0.42 * mode_mult
                # Rev limiter if exceeding max gear speed
                if self.speed_kmh >= max_gear_spd:
                    drive_force = 0.0  # Hit rev limiter!
                    self.motor_rpm = int(8200 + random.uniform(-50, 50))
                else:
                    drive_force = (self.throttle_pct / 100.0) * 38.0 * gear_torque_mult
                    # Motor RPM based on gear ratio
                    self.motor_rpm = int((self.speed_kmh / max(0.15, ratio)) * 48.0 + random.uniform(-10, 10))
        else:
            # AUTO mode - dynamically track active gear (D1-D6)
            if self.current_gear.startswith("D"):
                auto_gear = self.get_auto_gear_for_speed(self.speed_kmh)
                self.current_gear = f"D{auto_gear}"

            max_speed = 180.0 if self.drive_mode == "SPORT" else (100.0 if self.drive_mode == "ECO" else 145.0)
            drive_force = (self.throttle_pct / 100.0) * 48.0 * mode_mult
            if self.current_gear == "R":
                drive_force = -min(25.0, drive_force * 0.5)
            elif self.current_gear in ("P", "N"):
                drive_force = 0.0

            if self.speed_kmh >= max_speed:
                drive_force = 0.0

            if self.speed_kmh < 0.2 and self.current_gear in ("P", "N"):
                self.motor_rpm = int((self.throttle_pct / 100.0) * 6000.0) if self.current_gear == "N" else 0
            else:
                gear_num_str = self.current_gear[1:] if (self.current_gear.startswith("D") and len(self.current_gear) > 1) else "3"
                auto_ratio = self.GEAR_RATIOS.get(gear_num_str, 0.45)
                self.motor_rpm = int((self.speed_kmh / max(0.15, auto_ratio)) * 48.0 + random.uniform(-10, 10))

        # Braking force
        brake_force = (self.brake_pct / 100.0) * 75.0

        # Drag forces
        aero_drag = 0.00085 * (self.speed_kmh ** 2)
        rolling_resistance = 0.55 if self.speed_kmh > 0.1 else 0.0
        steer_scrub = (abs(self.steering_angle) / 40.0) * 0.02 * self.speed_kmh

        net_force = drive_force - brake_force - aero_drag - rolling_resistance - steer_scrub
        self.speed_kmh = max(0.0, self.speed_kmh + net_force * dt)

        if self.speed_kmh < 0.2:
            if self.throttle_pct < 1.0:
                self.motor_rpm = 0

        # 5. Electrical System Dynamics
        if self.throttle_pct > 1.0 and can_drive:
            base_draw = (self.throttle_pct / 100.0) * 260.0 * mode_mult
            self.battery_current = base_draw + random.uniform(-1.0, 1.0)
        elif self.brake_pct > 1.0 and self.speed_kmh > 3.0:
            regen_max = -80.0 if self.drive_mode != "ECO" else -95.0
            self.battery_current = (self.brake_pct / 100.0) * regen_max + random.uniform(-0.8, 0.8)
        else:
            self.battery_current = 2.0 + random.uniform(-0.2, 0.2)

        nominal_pack_v = 400.0
        internal_resistance = 0.045
        soc_factor = (self.battery_soc / 100.0) * 25.0
        self.battery_voltage = (nominal_pack_v - 25.0 + soc_factor) - (self.battery_current * internal_resistance)
        self.battery_power_kw = (self.battery_voltage * self.battery_current) / 1000.0

        energy_kwh = (self.battery_power_kw * (dt / 3600.0))
        pack_capacity_kwh = 60.0
        soc_delta = (energy_kwh / pack_capacity_kwh) * 100.0
        self.battery_soc = max(1.0, min(100.0, self.battery_soc - soc_delta))

        # Thermals
        ambient = 22.0
        motor_heat = ((self.motor_rpm / 9000.0) * 2.8 + (self.throttle_pct / 100.0) * 6.5) * dt
        motor_cool = (self.motor_temp_c - ambient) * 0.02 * (1.0 + self.speed_kmh / 50.0) * dt
        self.motor_temp_c = max(ambient, self.motor_temp_c + motor_heat - motor_cool)

        inverter_heat = (abs(self.battery_current) / 250.0) ** 1.8 * 8.5 * dt
        inverter_cool = (self.inverter_temp_c - ambient) * 0.018 * dt
        self.inverter_temp_c = max(ambient, self.inverter_temp_c + inverter_heat - inverter_cool)

        batt_heat = ((abs(self.battery_current) / 200.0) ** 2) * 1.4 * dt
        batt_cool = (self.battery_temp_c - ambient) * 0.005 * dt
        self.battery_temp_c = max(ambient, self.battery_temp_c + batt_heat - batt_cool)

        # Distance
        dist_delta = (self.speed_kmh * dt) / 3600.0
        self.trip_distance_km += dist_delta

    def _build_record(self) -> TelemetryRecord:
        warnings: List[str] = []
        if self.battery_soc < 15.0:
            warnings.append("LOW BATTERY")
        if self.battery_temp_c > 45.0 or self.motor_temp_c > 85.0 or self.inverter_temp_c > 75.0:
            warnings.append("THERMAL WARNING")
        if self.speed_kmh > 150.0:
            warnings.append("HIGH SPEED")
        if self.battery_current < -70.0:
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
            steering_angle=round(self.steering_angle, 1),
            gear=self.current_gear,
            transmission_mode=self.transmission_mode,
        )
