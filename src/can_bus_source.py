"""
Voltesse Dash - CAN Bus Telemetry Source & Frame Decoders
Engineered for automotive embedded deployment (SocketCAN on Linux/Raspberry Pi).
Decodes standard CAN frames for EV powertrain metrics:
- 0x100: Speed, RPM, Throttle %, Brake %, Drive Mode, Gear & Transmission
- 0x101: Battery SoC, Voltage, Current, Trip Distance
- 0x102: Thermals (Motor, Inverter, Battery, Ambient), Warnings, Steering Angle
Supports Automatic (PRNDB with dynamic gear display D1-D6) and Manual (1-6, N, R) modes.
Includes an integrated multi-threaded mock CAN transmitter for bench testing.
"""

import logging
import math
import struct
import threading
import time
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.database import TelemetryRecord

try:
    import can
except ImportError:
    can = None

logger = logging.getLogger("voltesse.can_bus")

# Standard CAN IDs
CAN_ID_SPEED_MOTOR = 0x100
CAN_ID_BATTERY = 0x101
CAN_ID_THERMALS_WARN = 0x102

DRIVE_MODE_MAP = {
    0: "ECO",
    1: "DRIVE",
    2: "SPORT",
}


class CANTelemetrySource(QThread):
    """
    QThread listening to a CAN interface (SocketCAN, virtual, or pcan)
    and emitting structured TelemetryRecord dataclasses.
    """

    telemetry_received = pyqtSignal(TelemetryRecord)
    status_changed = pyqtSignal(str)

    GEARS_AUTO = ["P", "R", "N", "D", "B"]
    GEARS_MANUAL = ["R", "N", "1", "2", "3", "4", "5", "6"]
    MODES = ["DRIVE", "SPORT", "ECO"]

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
        interface: Optional[str] = None,
        channel: Optional[str] = None,
        bitrate: int = 500000,
        enable_mock_bus: bool = False,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.interface = interface
        self.channel = channel
        self.bitrate = bitrate
        self.enable_mock_bus = enable_mock_bus

        self._bus: Optional["can.Bus"] = None
        self._running = False
        self._paused = False
        self._mock_transmitter: Optional["CANMockTransmitter"] = None

        # Transmission state
        self.transmission_mode = "AUTO"  # "AUTO" or "MANUAL"
        self.current_gear = "D1"

        # State cache for reconstructed telemetry
        self.speed_kmh = 0.0
        self.motor_rpm = 0
        self.battery_soc = 88.5
        self.battery_voltage = 398.0
        self.battery_current = 0.0
        self.battery_power_kw = 0.0
        self.battery_temp_c = 30.0
        self.motor_temp_c = 40.0
        self.inverter_temp_c = 35.0
        self.ambient_temp_c = 22.0
        self.throttle_pct = 0.0
        self.brake_pct = 0.0
        self.drive_mode = "DRIVE"
        self.trip_distance_km = 0.0
        self.steering_angle = 0.0
        self.warnings: List[str] = []

    def cycle_drive_mode(self) -> str:
        """Cycles drive modes (ECO -> DRIVE -> SPORT)."""
        curr_idx = self.MODES.index(self.drive_mode) if self.drive_mode in self.MODES else 0
        self.drive_mode = self.MODES[(curr_idx + 1) % len(self.MODES)]
        logger.info("CAN Telemetry Source drive mode changed to: %s", self.drive_mode)
        return self.drive_mode

    def toggle_transmission_mode(self) -> str:
        """Toggles between AUTO and MANUAL transmission."""
        if self.transmission_mode == "AUTO":
            self.transmission_mode = "MANUAL"
            self.current_gear = str(self.get_auto_gear_for_speed(self.speed_kmh))
        else:
            self.transmission_mode = "AUTO"
            if self.current_gear in ("P", "R", "N", "B"):
                pass
            else:
                self.current_gear = f"D{self.get_auto_gear_for_speed(self.speed_kmh)}"
        logger.info("CAN Telemetry Source transmission mode toggled to: %s", self.transmission_mode)
        return self.transmission_mode

    def shift_up(self) -> str:
        """Upshifts gear in manual or auto mode."""
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
        """Downshifts gear in manual or auto mode."""
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

    def _init_bus(self) -> bool:
        """Initializes the python-can Bus connection with multi-platform fallbacks."""
        if can is None:
            logger.warning("python-can is not installed; running in simulated CAN fallback mode.")
            return False

        candidates = []
        if self.interface and self.channel:
            candidates.append((self.interface, self.channel))

        candidates.append(("socketcan", "can0"))
        candidates.append(("virtual", "voltesse_vcan"))

        for iface, ch in candidates:
            try:
                logger.info("Attempting to connect CAN bus: interface=%s, channel=%s", iface, ch)
                self._bus = can.Bus(interface=iface, channel=ch, bitrate=self.bitrate)
                logger.info("Successfully initialized CAN bus (%s:%s)", iface, ch)
                return True
            except Exception as e:
                logger.debug("Could not open CAN bus on %s:%s: %s", iface, ch, e)

        try:
            self._bus = can.Bus(interface="virtual", channel="voltesse_default")
            logger.info("Initialized fallback in-memory virtual CAN bus.")
            return True
        except Exception as e:
            logger.error("Failed all CAN bus initialization attempts: %s", e)
            self._bus = None
            return False

    def run(self) -> None:
        """Main CAN receiver loop."""
        self._running = True
        self.status_changed.emit("CONNECTING")

        bus_ok = self._init_bus()
        if not bus_ok:
            self.status_changed.emit("CAN OFFLINE")

        if self.enable_mock_bus and self._bus is not None:
            self._mock_transmitter = CANMockTransmitter(self._bus, source=self)
            self._mock_transmitter.start()

        self.status_changed.emit("CAN ACTIVE" if bus_ok else "CAN SIMULATED")

        last_emit = time.time()
        while self._running:
            if self._bus is not None:
                try:
                    msg = self._bus.recv(timeout=0.05)
                    if msg is not None:
                        self._decode_message(msg)
                except Exception as e:
                    logger.debug("Error receiving CAN message: %s", e)
            else:
                self.msleep(50)

            now = time.time()
            if now - last_emit >= 0.05 and not self._paused:
                last_emit = now
                rec = self._build_record()
                self.telemetry_received.emit(rec)

        if self._mock_transmitter:
            self._mock_transmitter.stop()

        if self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception:
                pass
            self._bus = None

        self.status_changed.emit("STOPPED")

    def stop(self) -> None:
        """Gracefully stops the CAN listener thread."""
        self._running = False
        self.wait(2000)

    def toggle_pause(self) -> bool:
        self._paused = not self._paused
        self.status_changed.emit("PAUSED" if self._paused else "CAN ACTIVE")
        return self._paused

    def _decode_message(self, msg: "can.Message") -> None:
        """Decodes raw binary CAN message payloads according to arbitration ID."""
        data = msg.data
        if not data or len(data) < 6:
            return

        try:
            if msg.arbitration_id == CAN_ID_SPEED_MOTOR:
                # Format: >H H B B B (Speed * 10, Motor RPM, Throttle, Brake, Mode)
                speed_raw, rpm, thr, brk, mode_code = struct.unpack_from(">HHBBB", data, 0)
                self.speed_kmh = speed_raw / 10.0
                self.motor_rpm = rpm
                self.throttle_pct = float(thr)
                self.brake_pct = float(brk)
                self.drive_mode = DRIVE_MODE_MAP.get(mode_code, "DRIVE")

                if len(data) >= 8:
                    gear_byte = data[7]
                    # Bit 7: Manual flag
                    is_manual = bool(gear_byte & 0x80)
                    if is_manual:
                        self.transmission_mode = "MANUAL"
                        gear_num = gear_byte & 0x0F
                        if 1 <= gear_num <= 6:
                            self.current_gear = str(gear_num)
                        elif gear_num == 0:
                            self.current_gear = "N"
                        elif gear_num == 0x0E:
                            self.current_gear = "R"
                    elif self.transmission_mode == "AUTO":
                        gear_code = gear_byte & 0x07
                        auto_map = {0: "P", 1: "R", 2: "N", 3: "D", 4: "B"}
                        if gear_code in auto_map:
                            base_g = auto_map[gear_code]
                            if base_g == "D":
                                self.current_gear = f"D{self.get_auto_gear_for_speed(self.speed_kmh)}"
                            else:
                                self.current_gear = base_g

            elif msg.arbitration_id == CAN_ID_BATTERY:
                soc_raw, volt_raw, curr_raw, dist_raw = struct.unpack_from(">HHhH", data, 0)
                self.battery_soc = soc_raw / 10.0
                self.battery_voltage = volt_raw / 10.0
                self.battery_current = curr_raw / 10.0
                self.battery_power_kw = (self.battery_voltage * self.battery_current) / 1000.0
                self.trip_distance_km = dist_raw / 10.0

            elif msg.arbitration_id == CAN_ID_THERMALS_WARN:
                bt, mt, it, amb, warn_bits, steer_raw = struct.unpack_from(">BBBBHh", data, 0)
                self.battery_temp_c = float(bt - 40)
                self.motor_temp_c = float(mt - 40)
                self.inverter_temp_c = float(it - 40)
                self.ambient_temp_c = float(amb - 40)
                self.steering_angle = steer_raw / 10.0

                warnings: List[str] = []
                if warn_bits & 0x01:
                    warnings.append("LOW BATTERY")
                if warn_bits & 0x02:
                    warnings.append("THERMAL WARNING")
                if warn_bits & 0x04:
                    warnings.append("HIGH SPEED")
                if warn_bits & 0x08:
                    warnings.append("CAN BUS ERROR")
                self.warnings = warnings
        except Exception as e:
            logger.debug("Failed to unpack CAN message ID 0x%X: %s", msg.arbitration_id, e)

    def _build_record(self) -> TelemetryRecord:
        """Constructs TelemetryRecord from currently decoded CAN state."""
        gear_val = self.current_gear
        if self.transmission_mode == "AUTO":
            if gear_val.startswith("D") or gear_val == "D":
                gear_val = f"D{self.get_auto_gear_for_speed(self.speed_kmh)}"

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
            warnings=list(self.warnings),
            steering_angle=round(self.steering_angle, 1),
            gear=gear_val,
            transmission_mode=self.transmission_mode,
        )


class CANMockTransmitter(threading.Thread):
    """
    Background transmitter that generates realistic CAN frames on a virtual or loopback CAN bus.
    Used for hardware bench verification and testing without requiring a live racecar ECU.
    """

    def __init__(
        self,
        bus: "can.Bus",
        source: Optional["CANTelemetrySource"] = None,
        update_rate_hz: float = 20.0,
    ):
        super().__init__(name="CANMockTransmitter", daemon=True)
        self.bus = bus
        self.source = source
        self.interval = 1.0 / max(1.0, update_rate_hz)
        self._running = False

    def run(self) -> None:
        if can is None or self.bus is None:
            return

        self._running = True
        t0 = time.time()
        speed = 45.0
        soc = 88.5
        dist = 1.2

        while self._running:
            now = time.time()
            elapsed = now - t0

            speed = max(0.0, 60.0 + 35.0 * (1.0 + struct.unpack("f", struct.pack("f", float(time.time() % 10 - 5)))[0] * 0.1))
            rpm = int(speed * 78.5)
            thr = 40.0 if speed < 80.0 else 20.0
            brk = 0.0

            if self.source:
                mode_str = self.source.drive_mode
                mode = 0 if mode_str == "ECO" else (2 if mode_str == "SPORT" else 1)
                if self.source.transmission_mode == "MANUAL":
                    g = self.source.current_gear
                    g_num = int(g) if g.isdigit() else (0 if g == "N" else (0x0E if g == "R" else 1))
                    gear_byte = 0x80 | (g_num & 0x0F)
                else:
                    auto_map_rev = {"P": 0, "R": 1, "N": 2, "D": 3, "B": 4}
                    base_g = self.source.current_gear[0] if self.source.current_gear else "D"
                    gear_byte = auto_map_rev.get(base_g, 3)
            else:
                mode = 1  # DRIVE
                gear_byte = 3  # D in auto

            f1_data = struct.pack(">HHBBBBx", int(speed * 10), rpm, int(thr), int(brk), mode, gear_byte)
            msg1 = can.Message(arbitration_id=CAN_ID_SPEED_MOTOR, data=f1_data, is_extended_id=False)

            soc = max(10.0, soc - 0.002)
            volt = 398.0 - (thr * 0.1)
            curr = thr * 1.5
            dist += (speed / 3600.0) * self.interval
            f2_data = struct.pack(">HHhH", int(soc * 10), int(volt * 10), int(curr * 10), int(dist * 10))
            msg2 = can.Message(arbitration_id=CAN_ID_BATTERY, data=f2_data, is_extended_id=False)

            steer = 0.0
            f3_data = struct.pack(">BBBBHh", int(32 + 40), int(48 + 40), int(41 + 40), int(22 + 40), 0, int(steer * 10))
            msg3 = can.Message(arbitration_id=CAN_ID_THERMALS_WARN, data=f3_data, is_extended_id=False)

            try:
                self.bus.send(msg1)
                self.bus.send(msg2)
                self.bus.send(msg3)
            except Exception:
                pass

            time.sleep(self.interval)

    def stop(self) -> None:
        self._running = False
