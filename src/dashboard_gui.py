"""
Voltesse Dash - Modern Automotive Digital Cockpit GUI
A high-contrast, sleek, distraction-free instrument cluster engineered for embedded
in-vehicle displays (e.g. Raspberry Pi automotive HUD / cluster screens).
"""

from collections import deque
import math
import time
from typing import Deque, List, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.database import TelemetryRecord


# =====================================================================
# Modern Automotive Color Palette (OLED High-Contrast Cyber-Cluster)
# =====================================================================
COLOR_BG_DARK = QColor("#04060A")
COLOR_PANEL_BG = QColor(10, 14, 22, 230)
COLOR_PANEL_BORDER = QColor(30, 41, 59, 180)
COLOR_CYAN = QColor("#00F0FF")
COLOR_CYAN_DIM = QColor(0, 240, 255, 60)
COLOR_BLUE = QColor("#3B82F6")
COLOR_GREEN = QColor("#10B981")
COLOR_GREEN_DIM = QColor(16, 185, 129, 60)
COLOR_AMBER = QColor("#F59E0B")
COLOR_RED = QColor("#EF4444")
COLOR_TEXT_PRIMARY = QColor("#FFFFFF")
COLOR_TEXT_SECONDARY = QColor("#94A3B8")
COLOR_TEXT_MUTED = QColor("#475569")
COLOR_GAUGE_TRACK = QColor(16, 22, 34, 220)
COLOR_GAUGE_TRACK_ACCENT = QColor(24, 32, 48, 240)


class SpeedometerDialWidget(QWidget):
    """
    Sleek, modern automotive central speedometer.
    Features precision graduation ticks, glowing gradient speed sweep,
    large digital readout, gear selector ribbon, and live throttle/brake micro-meters.
    """

    def __init__(
        self,
        min_val: float = 0.0,
        max_val: float = 180.0,
        title: str = "SPEED",
        unit: str = "KM/H",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.title = title
        self.unit = unit
        self.current_val = 0.0
        self.sub_val_label = "RPM"
        self.sub_val = "0"
        self.throttle_pct = 0.0
        self.brake_pct = 0.0
        self.active_gear = "D"
        self.drive_mode = "DRIVE"

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(280, 280)

    def set_value(self, value: float, sub_val: str = "") -> None:
        self.current_val = max(self.min_val, min(self.max_val, value))
        if sub_val:
            self.sub_val = sub_val
        self.update()

    def set_pedals_and_gear(self, throttle: float, brake: float, gear: str = "D", mode: str = "DRIVE") -> None:
        self.throttle_pct = throttle
        self.brake_pct = brake
        self.active_gear = gear
        self.drive_mode = mode
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        cx = w / 2.0
        cy = h / 2.0

        # Primary Gauge Arc Radii
        outer_r = (side / 2.0) - 16.0
        inner_r = outer_r - 18.0

        # Geometry angles (Start at bottom-left 225 deg, sweep 270 deg clockwise to bottom-right)
        start_angle_deg = 225.0
        total_span_deg = -270.0

        # 1. Subtle Outer Ambient Glow Ring
        glow_grad = QRadialGradient(QPointF(cx, cy), outer_r + 10)
        glow_grad.setColorAt(0.75, QColor(0, 0, 0, 0))
        glow_grad.setColorAt(0.92, QColor(0, 240, 255, 18))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), outer_r + 10, outer_r + 10)

        # 2. Main Gauge Track (Smoked Titanium)
        gauge_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
        pen_track = QPen(COLOR_GAUGE_TRACK, 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_track)
        painter.drawArc(gauge_rect, int(start_angle_deg * 16), int(total_span_deg * 16))

        # 3. Precision Graduation Ticks
        num_ticks = 19  # Every 10 km/h from 0 to 180
        for i in range(num_ticks):
            val = i * 10
            fraction = i / (num_ticks - 1)
            angle_deg = start_angle_deg + (total_span_deg * fraction)
            rad = math.radians(-angle_deg)  # Math angles are CCW from 3 o'clock

            is_major = (i % 3 == 0)  # 0, 30, 60, 90, 120, 150, 180
            tick_len = 10 if is_major else 5
            tick_width = 2.0 if is_major else 1.0

            # Tick line
            r_start = outer_r + 4
            r_end = r_start + tick_len
            x1 = cx + math.cos(rad) * r_start
            y1 = cy + math.sin(rad) * r_start
            x2 = cx + math.cos(rad) * r_end
            y2 = cy + math.sin(rad) * r_end

            tick_color = COLOR_TEXT_SECONDARY if is_major else COLOR_TEXT_MUTED
            if fraction <= (self.current_val / self.max_val):
                tick_color = COLOR_CYAN if fraction < 0.7 else COLOR_AMBER

            painter.setPen(QPen(tick_color, tick_width))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Major Tick Numbers
            if is_major and side > 220:
                r_num = outer_r + 20
                nx = cx + math.cos(rad) * r_num
                ny = cy + math.sin(rad) * r_num
                painter.setPen(COLOR_TEXT_MUTED if fraction > (self.current_val / self.max_val) else COLOR_TEXT_SECONDARY)
                font_tick = QFont("Segoe UI", int(side * 0.038), QFont.Weight.Bold)
                painter.setFont(font_tick)
                painter.drawText(QRectF(nx - 16, ny - 10, 32, 20), Qt.AlignmentFlag.AlignCenter, str(val))

        # 4. Active Speed Glowing Ribbon
        fraction = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        active_span_deg = total_span_deg * fraction

        if fraction > 0.005:
            # Dynamic speed color transition: Neon Cyan -> Electric Cobalt -> Amber
            if fraction < 0.55:
                sweep_color = COLOR_CYAN
            elif fraction < 0.82:
                sweep_color = COLOR_BLUE
            else:
                sweep_color = COLOR_AMBER

            pen_sweep = QPen(sweep_color, 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
            painter.setPen(pen_sweep)
            painter.drawArc(gauge_rect, int(start_angle_deg * 16), int(active_span_deg * 16))

            # Glowing needle head beacon
            tip_angle = start_angle_deg + active_span_deg
            tip_rad = math.radians(-tip_angle)
            tip_x = cx + math.cos(tip_rad) * outer_r
            tip_y = cy + math.sin(tip_rad) * outer_r

            painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
            painter.setPen(QPen(sweep_color, 2))
            painter.drawEllipse(QPointF(tip_x, tip_y), 4.5, 4.5)

        # 5. Inner Accent Halo
        pen_inner = QPen(QColor(30, 41, 59, 100), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen_inner)
        painter.drawArc(
            QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2),
            int(start_angle_deg * 16),
            int(total_span_deg * 16),
        )

        # 6. Central Digital Speedometer Readout
        speed_int = int(round(self.current_val))
        font_speed = QFont("Segoe UI", int(side * 0.26), QFont.Weight.Bold)
        font_speed.setStyleHint(QFont.StyleHint.SansSerif)
        painter.setFont(font_speed)
        painter.setPen(COLOR_TEXT_PRIMARY)

        speed_rect = QRectF(cx - outer_r, cy - outer_r * 0.55, outer_r * 2, outer_r * 0.75)
        painter.drawText(speed_rect, Qt.AlignmentFlag.AlignCenter, f"{speed_int}")

        # 7. Speed Unit Label
        painter.setPen(COLOR_CYAN)
        font_unit = QFont("Segoe UI", int(side * 0.055), QFont.Weight.DemiBold)
        font_unit.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(font_unit)
        unit_rect = QRectF(cx - outer_r, cy + outer_r * 0.12, outer_r * 2, outer_r * 0.22)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, self.unit)

        # 8. Motor RPM & Gear Selector Badge (e.g. P R N [D] B)
        gear_y = cy + outer_r * 0.35
        gears = ["P", "R", "N", "D", "B"]
        font_gear = QFont("Segoe UI", int(side * 0.048), QFont.Weight.Bold)
        painter.setFont(font_gear)

        total_gear_w = len(gears) * 22
        start_gx = cx - (total_gear_w / 2.0)

        for idx, g in enumerate(gears):
            gx = start_gx + idx * 22
            g_rect = QRectF(gx, gear_y, 20, 20)
            if g == self.active_gear:
                # Active gear glowing badge
                painter.setBrush(QBrush(QColor(0, 240, 255, 45)))
                painter.setPen(QPen(COLOR_CYAN, 1.5))
                painter.drawRoundedRect(g_rect, 4, 4)
                painter.setPen(COLOR_CYAN)
            else:
                painter.setPen(COLOR_TEXT_MUTED)
            painter.drawText(g_rect, Qt.AlignmentFlag.AlignCenter, g)

        # RPM Subtitle
        painter.setPen(COLOR_TEXT_SECONDARY)
        font_rpm = QFont("Consolas", int(side * 0.04), QFont.Weight.Normal)
        painter.setFont(font_rpm)
        rpm_rect = QRectF(cx - outer_r, cy + outer_r * 0.58, outer_r * 2, outer_r * 0.22)
        painter.drawText(rpm_rect, Qt.AlignmentFlag.AlignCenter, f"{self.sub_val_label} {self.sub_val}")

        # 9. Dual Vertical Micro-Bars for Throttle (Cyan) & Brake (Coral Red)
        bar_w = 4.0
        bar_h = outer_r * 0.65
        bar_y = cy - (bar_h / 2.0)

        # Throttle Bar (Right side of center)
        thr_x = cx + outer_r * 0.62
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(thr_x, bar_y, bar_w, bar_h), 2, 2)
        thr_fill_h = bar_h * (min(100.0, self.throttle_pct) / 100.0)
        if thr_fill_h > 0:
            painter.setBrush(QBrush(COLOR_CYAN))
            painter.drawRoundedRect(QRectF(thr_x, bar_y + bar_h - thr_fill_h, bar_w, thr_fill_h), 2, 2)

        # Brake Bar (Left side of center)
        brk_x = cx - outer_r * 0.62 - bar_w
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(brk_x, bar_y, bar_w, bar_h), 2, 2)
        brk_fill_h = bar_h * (min(100.0, self.brake_pct) / 100.0)
        if brk_fill_h > 0:
            painter.setBrush(QBrush(COLOR_RED))
            painter.drawRoundedRect(QRectF(brk_x, bar_y + bar_h - brk_fill_h, bar_w, brk_fill_h), 2, 2)

        painter.end()


# Alias for backward compatibility with existing tests
ArcGaugeWidget = SpeedometerDialWidget


class BatteryStatusWidget(QWidget):
    """
    Sleek automotive left-wing module:
    Swept Battery SoC arc, dynamic color grading, estimated range HUD,
    pack voltage and live current draw.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.soc = 100.0
        self.voltage = 400.0
        self.current = 0.0
        self.est_range_km = 340.0
        self.setMinimumSize(220, 200)

    def set_battery_data(self, soc: float, voltage: float, current: float) -> None:
        self.soc = max(0.0, min(100.0, soc))
        self.voltage = voltage
        self.current = current
        self.est_range_km = self.soc * 4.2  # Approx 4.2 km per % SoC
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

        # Dynamic Battery Theme Color
        if self.soc > 30.0:
            bar_color = COLOR_GREEN
            glow_color = COLOR_GREEN_DIM
        elif self.soc > 15.0:
            bar_color = COLOR_AMBER
            glow_color = QColor(245, 158, 11, 60)
        else:
            bar_color = COLOR_RED
            glow_color = QColor(239, 68, 68, 60)

        # 1. Module Header
        painter.setPen(COLOR_TEXT_SECONDARY)
        font_hdr = QFont("Segoe UI", 9, QFont.Weight.Bold)
        font_hdr.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        painter.setFont(font_hdr)
        painter.drawText(QRectF(0, 0, w, 18), Qt.AlignmentFlag.AlignLeft, "⚡ ENERGY & BATTERY")

        # 2. Sleek Swept Battery Arc
        arc_cx = 64.0
        arc_cy = 78.0
        arc_r = 44.0
        arc_rect = QRectF(arc_cx - arc_r, arc_cy - arc_r, arc_r * 2, arc_r * 2)

        # Track arc (Sweeping 240 degrees from 210 to -30)
        start_ang = 210.0
        span_ang = -240.0
        pen_track = QPen(COLOR_GAUGE_TRACK, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_track)
        painter.drawArc(arc_rect, int(start_ang * 16), int(span_ang * 16))

        # Active SoC Arc
        active_span = span_ang * (self.soc / 100.0)
        if self.soc > 0.5:
            pen_active = QPen(bar_color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_active)
            painter.drawArc(arc_rect, int(start_ang * 16), int(active_span * 16))

        # SoC Percentage Digits inside Arc
        painter.setPen(COLOR_TEXT_PRIMARY)
        font_soc = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(font_soc)
        painter.drawText(arc_rect, Qt.AlignmentFlag.AlignCenter, f"{int(round(self.soc))}%")

        # 3. Estimated Range Readout (Right of the Arc)
        range_x = 126.0
        painter.setPen(COLOR_TEXT_MUTED)
        font_sub = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(font_sub)
        painter.drawText(QRectF(range_x, 38, w - range_x, 14), Qt.AlignmentFlag.AlignLeft, "EST. RANGE")

        painter.setPen(COLOR_CYAN)
        font_range = QFont("Segoe UI", 20, QFont.Weight.Bold)
        painter.setFont(font_range)
        painter.drawText(QRectF(range_x, 52, w - range_x, 28), Qt.AlignmentFlag.AlignLeft, f"{int(self.est_range_km)}")

        painter.setPen(COLOR_TEXT_SECONDARY)
        font_unit = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        painter.setFont(font_unit)
        painter.drawText(QRectF(range_x + 58, 62, 40, 16), Qt.AlignmentFlag.AlignLeft, "KM")

        # 4. Energy Stats Strip (Voltage & Current Draw in Smoked Glass Pods)
        pod_y = 132.0
        pod_w = (w - 8) / 2.0
        pod_h = 48.0

        # Voltage Pod
        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, pod_y, pod_w, pod_h), 6, 6)

        painter.setPen(COLOR_TEXT_MUTED)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(6, pod_y + 4, pod_w - 12, 14), Qt.AlignmentFlag.AlignLeft, "PACK VOLTAGE")

        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        painter.drawText(QRectF(6, pod_y + 20, pod_w - 12, 22), Qt.AlignmentFlag.AlignLeft, f"{self.voltage:.1f} V")

        # Current Draw Pod
        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(pod_w + 8, pod_y, pod_w, pod_h), 6, 6)

        painter.setPen(COLOR_TEXT_MUTED)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(pod_w + 14, pod_y + 4, pod_w - 12, 14), Qt.AlignmentFlag.AlignLeft, "CURRENT")

        curr_color = COLOR_GREEN if self.current < -0.5 else (COLOR_AMBER if self.current > 80.0 else COLOR_TEXT_PRIMARY)
        painter.setPen(curr_color)
        painter.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        painter.drawText(QRectF(pod_w + 14, pod_y + 20, pod_w - 12, 22), Qt.AlignmentFlag.AlignLeft, f"{self.current:+.1f} A")

        painter.end()


class PowerBarWidget(QWidget):
    """
    Sleek automotive bidirectional power bar meter.
    Regen (< 0 kW) on left in Emerald Green; Discharge (> 0 kW) on right in Cyan / Amber.
    """

    def __init__(self, max_kw: float = 120.0, max_regen_kw: float = 60.0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.max_kw = max_kw
        self.max_regen_kw = max_regen_kw
        self.power_kw = 0.0
        self.setMinimumHeight(32)

    def set_power(self, power_kw: float) -> None:
        self.power_kw = power_kw
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_h = 10.0
        y = (h - bar_h) / 2.0

        # Background track
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, y, w, bar_h), 4, 4)

        # Center split marker
        center_x = w * (self.max_regen_kw / (self.max_kw + self.max_regen_kw))
        painter.setPen(QPen(COLOR_TEXT_MUTED, 1.5))
        painter.drawLine(int(center_x), int(y - 2), int(center_x), int(y + bar_h + 2))

        # Active Fill
        if self.power_kw < -0.2:
            # Regen (leftwards)
            ratio = min(1.0, abs(self.power_kw) / self.max_regen_kw)
            fill_w = center_x * ratio
            fill_rect = QRectF(center_x - fill_w, y, fill_w, bar_h)
            painter.setBrush(QBrush(COLOR_GREEN))
            painter.drawRoundedRect(fill_rect, 3, 3)
        elif self.power_kw > 0.2:
            # Discharge (rightwards)
            ratio = min(1.0, self.power_kw / self.max_kw)
            fill_w = (w - center_x) * ratio
            fill_rect = QRectF(center_x, y, fill_w, bar_h)
            color = COLOR_AMBER if self.power_kw > (self.max_kw * 0.7) else COLOR_CYAN
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(fill_rect, 3, 3)

        painter.end()


class LiveSparklineWidget(QWidget):
    """
    Real-time rolling oscilloscope telemetry wave on smoked glass.
    """

    def __init__(self, max_points: int = 50, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.max_points = max_points
        self.speed_history: Deque[float] = deque(maxlen=max_points)
        self.power_history: Deque[float] = deque(maxlen=max_points)
        self.setMinimumHeight(44)

        for _ in range(max_points):
            self.speed_history.append(0.0)
            self.power_history.append(0.0)

    def add_data_point(self, speed: float, power: float) -> None:
        self.speed_history.append(speed)
        self.power_history.append(power)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Smoked grid frame
        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 6, 6)

        # Subtle oscilloscope grid lines
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1, Qt.PenStyle.DotLine))
        painter.drawLine(0, int(h * 0.33), w, int(h * 0.33))
        painter.drawLine(0, int(h * 0.66), w, int(h * 0.66))

        count = len(self.speed_history)
        if count < 2:
            painter.end()
            return

        step_x = (w - 4) / (self.max_points - 1)

        # 1. Speed Trace (Glowing Cyan)
        max_speed = 180.0
        speed_path = QPainterPath()
        for i, val in enumerate(self.speed_history):
            clamped = max(0.0, min(max_speed, val))
            y = h - (clamped / max_speed) * (h - 8) - 4
            x = 2 + (i * step_x)
            if i == 0:
                speed_path.moveTo(x, y)
            else:
                speed_path.lineTo(x, y)

        painter.setPen(QPen(COLOR_CYAN, 1.8))
        painter.drawPath(speed_path)

        # 2. Power Trace (Amber/Orange)
        max_power = 120.0
        power_path = QPainterPath()
        for i, val in enumerate(self.power_history):
            clamped = max(-40.0, min(max_power, val))
            y = h - ((clamped + 40.0) / (max_power + 40.0)) * (h - 8) - 4
            x = 2 + (i * step_x)
            if i == 0:
                power_path.moveTo(x, y)
            else:
                power_path.lineTo(x, y)

        painter.setPen(QPen(COLOR_AMBER, 1.2, Qt.PenStyle.DashLine))
        painter.drawPath(power_path)

        # Micro Legend
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.setPen(COLOR_CYAN)
        painter.drawText(6, 11, "SPD")
        painter.setPen(COLOR_AMBER)
        painter.drawText(32, 11, "PWR")

        painter.end()


class ThermalMonitorWidget(QWidget):
    """
    Automotive Powertrain Thermal Monitor (Motor, Inverter, Battery).
    Displays temperature status with graduated safety color coding.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.motor_temp = 0.0
        self.inverter_temp = 0.0
        self.batt_temp = 0.0
        self.setFixedHeight(38)

    def set_temperatures(self, motor: float, inverter: float, battery: float) -> None:
        self.motor_temp = motor
        self.inverter_temp = inverter
        self.batt_temp = battery
        self.update()

    def _temp_color(self, temp: float, warn_th: float, crit_th: float) -> QColor:
        if temp >= crit_th:
            return COLOR_RED
        elif temp >= warn_th:
            return COLOR_AMBER
        return COLOR_GREEN

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        items = [
            ("MOTOR", self.motor_temp, 75.0, 90.0),
            ("INVERTER", self.inverter_temp, 65.0, 80.0),
            ("BATTERY", self.batt_temp, 42.0, 50.0),
        ]

        col_w = w / len(items)

        for i, (label, temp, warn_th, crit_th) in enumerate(items):
            box_x = i * col_w + 3
            box_w = col_w - 6
            color = self._temp_color(temp, warn_th, crit_th)

            # Background pod
            painter.setBrush(QBrush(COLOR_PANEL_BG))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
            painter.drawRoundedRect(QRectF(box_x, 0, box_w, 36), 5, 5)

            # Label
            painter.setPen(COLOR_TEXT_MUTED)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(box_x + 6, 2, box_w - 12, 14), Qt.AlignmentFlag.AlignLeft, label)

            # Value & Status pip
            painter.setPen(color)
            painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            painter.drawText(QRectF(box_x + 6, 16, box_w - 22, 18), Qt.AlignmentFlag.AlignLeft, f"{temp:.1f}°C")

            # Mini status pip
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(box_x + box_w - 10, 18), 3, 3)

        painter.end()


class VoltesseDashboard(QMainWindow):
    """
    Main Automotive Digital Cockpit Cluster Window.
    Distraction-free, modern, sleek, high-information-density UI.
    """

    drive_mode_requested = pyqtSignal()
    pause_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voltesse Dash - Digital Cockpit")
        self.setMinimumSize(960, 540)
        self.resize(1280, 720)

        # Style sheet (Seamless Dark Glass Automotive Cluster)
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #04060A;
            }
            QWidget {
                color: #FFFFFF;
            }
            """
        )

        self._build_ui()

        # Real-time UI Clock timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    def _build_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 8, 14, 10)
        main_layout.setSpacing(6)

        # -------------------------------------------------------------
        # 1. TOP AUTOMOTIVE HUD RIBBON
        # -------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setFixedHeight(38)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 0, 6, 0)
        top_layout.setSpacing(10)

        # Turn Signal Left
        self.left_blinker = QLabel("◄")
        self.left_blinker.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.left_blinker.setStyleSheet("color: #1E293B;")

        # Brand / Subtitle
        brand_label = QLabel("⚡ VOLTESSE")
        brand_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Black))
        brand_label.setStyleSheet("color: #00F0FF; letter-spacing: 2px;")

        # Ready Indicator
        self.ready_badge = QLabel("READY")
        self.ready_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.ready_badge.setStyleSheet(
            "color: #10B981; background-color: rgba(16, 185, 129, 0.15); padding: 2px 8px; border-radius: 4px;"
        )

        # Drive Mode Pill
        self.mode_badge = QLabel("DRIVE")
        self.mode_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.mode_badge.setStyleSheet(
            "background-color: rgba(59, 130, 246, 0.2); color: #60A5FA; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(59, 130, 246, 0.4);"
        )

        # Status / Warning Pill
        self.status_badge = QLabel("SYSTEM READY")
        self.status_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.status_badge.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.12); color: #34D399; padding: 2px 10px; border-radius: 4px;"
        )

        # Ambient Temp
        self.ambient_label = QLabel("22°C")
        self.ambient_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.ambient_label.setStyleSheet("color: #94A3B8;")

        # Live Clock
        self.clock_label = QLabel("00:00:00")
        self.clock_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.clock_label.setStyleSheet("color: #FFFFFF;")

        # Turn Signal Right
        self.right_blinker = QLabel("►")
        self.right_blinker.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.right_blinker.setStyleSheet("color: #1E293B;")

        top_layout.addWidget(self.left_blinker)
        top_layout.addSpacing(4)
        top_layout.addWidget(brand_label)
        top_layout.addSpacing(6)
        top_layout.addWidget(self.ready_badge)
        top_layout.addStretch(1)
        top_layout.addWidget(self.mode_badge)
        top_layout.addSpacing(6)
        top_layout.addWidget(self.status_badge)
        top_layout.addStretch(1)
        top_layout.addWidget(self.ambient_label)
        top_layout.addSpacing(10)
        top_layout.addWidget(self.clock_label)
        top_layout.addSpacing(4)
        top_layout.addWidget(self.right_blinker)

        main_layout.addWidget(top_bar)

        # -------------------------------------------------------------
        # 2. MAIN COCKPIT PANORAMIC STAGE (Wings + Central Dial)
        # -------------------------------------------------------------
        stage_layout = QHBoxLayout()
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setSpacing(12)

        # --- LEFT WING: Energy, Battery, Range ---
        left_wing = QFrame()
        left_wing.setStyleSheet("background: transparent;")
        left_wing_layout = QVBoxLayout(left_wing)
        left_wing_layout.setContentsMargins(10, 4, 10, 4)
        left_wing_layout.setSpacing(6)

        self.battery_widget = BatteryStatusWidget()
        left_wing_layout.addWidget(self.battery_widget)

        # Amperage alias label for test compatibility
        self.amp_val = QLabel("0.0 A")
        self.amp_val.setVisible(False)
        left_wing_layout.addWidget(self.amp_val)

        stage_layout.addWidget(left_wing, stretch=3)

        # --- CENTER STAGE: Primary Speedometer Dial ---
        center_stage = QFrame()
        center_stage.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center_stage)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.speed_gauge = SpeedometerDialWidget(min_val=0.0, max_val=180.0, title="SPEED", unit="KM/H")
        center_layout.addWidget(self.speed_gauge)

        stage_layout.addWidget(center_stage, stretch=4)

        # --- RIGHT WING: Powertrain Dynamics, Net Power, Pedals ---
        right_wing = QFrame()
        right_wing.setStyleSheet("background: transparent;")
        right_wing_layout = QVBoxLayout(right_wing)
        right_wing_layout.setContentsMargins(10, 4, 10, 4)
        right_wing_layout.setSpacing(6)

        # Right Header
        right_hdr = QLabel("⚡ POWERTRAIN DYNAMICS")
        right_hdr.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        right_hdr.setStyleSheet("color: #94A3B8; letter-spacing: 1px;")
        right_wing_layout.addWidget(right_hdr)

        # Net Power Numerical Readout Pod
        power_pod = QFrame()
        power_pod.setStyleSheet("background-color: rgba(10, 14, 22, 0.9); border: 1px solid rgba(30, 41, 59, 0.7); border-radius: 6px;")
        power_pod_layout = QHBoxLayout(power_pod)
        power_pod_layout.setContentsMargins(10, 6, 10, 6)

        power_title = QLabel("NET POWER")
        power_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        power_title.setStyleSheet("color: #64748B;")

        self.power_val = QLabel("0.0 kW")
        self.power_val.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self.power_val.setStyleSheet("color: #00F0FF;")

        power_pod_layout.addWidget(power_title)
        power_pod_layout.addStretch(1)
        power_pod_layout.addWidget(self.power_val)
        right_wing_layout.addWidget(power_pod)

        # Power / Regen Bar
        self.power_bar = PowerBarWidget()
        right_wing_layout.addWidget(self.power_bar)

        # Dynamic Pedals Status Strip
        pedal_frame = QFrame()
        pedal_layout = QHBoxLayout(pedal_frame)
        pedal_layout.setContentsMargins(0, 0, 0, 0)

        self.throttle_label = QLabel("THR: 0%")
        self.throttle_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.throttle_label.setStyleSheet("color: #00F0FF;")

        self.brake_label = QLabel("BRK: 0%")
        self.brake_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.brake_label.setStyleSheet("color: #EF4444;")

        pedal_layout.addWidget(self.throttle_label)
        pedal_layout.addStretch(1)
        pedal_layout.addWidget(self.brake_label)
        right_wing_layout.addWidget(pedal_frame)

        # Mini Live Waveform inside Right Wing
        self.sparkline_widget = LiveSparklineWidget(max_points=50)
        self.sparkline_widget.setFixedHeight(48)
        right_wing_layout.addWidget(self.sparkline_widget)

        stage_layout.addWidget(right_wing, stretch=3)

        main_layout.addLayout(stage_layout, stretch=4)

        # -------------------------------------------------------------
        # 3. BOTTOM TELEMETRY & TRIP DECK
        # -------------------------------------------------------------
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet(
            "background-color: rgba(10, 14, 22, 0.85); border: 1px solid rgba(30, 41, 59, 0.6); border-radius: 8px;"
        )
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(12, 6, 12, 6)
        bottom_layout.setSpacing(16)

        # Trip Stats Pod
        trip_box = QVBoxLayout()
        trip_hdr = QLabel("TRIP ODOMETER")
        trip_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        trip_hdr.setStyleSheet("color: #64748B;")
        self.trip_dist_val = QLabel("0.00 km")
        self.trip_dist_val.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.trip_dist_val.setStyleSheet("color: #FFFFFF;")
        trip_box.addWidget(trip_hdr)
        trip_box.addWidget(self.trip_dist_val)
        bottom_layout.addLayout(trip_box, stretch=1)

        # Thermal Diagnostics Pods
        self.thermal_widget = ThermalMonitorWidget()
        bottom_layout.addWidget(self.thermal_widget, stretch=3)

        main_layout.addWidget(bottom_bar, stretch=1)

    def _update_clock(self) -> None:
        self.clock_label.setText(time.strftime("%H:%M:%S"))

    def update_telemetry(self, record: TelemetryRecord) -> None:
        """
        Non-blocking slot updating all telemetry gauges and HUD indicators.
        """
        # Speedometer, RPM, Pedals, Gear
        gear = "D"
        if record.speed_kmh < 0.2 and record.brake_pct > 10.0:
            gear = "P"
        elif record.speed_kmh > 0.5 and record.battery_power_kw < -15.0:
            gear = "B"

        self.speed_gauge.set_value(record.speed_kmh, sub_val=str(record.motor_rpm))
        self.speed_gauge.set_pedals_and_gear(
            throttle=record.throttle_pct,
            brake=record.brake_pct,
            gear=gear,
            mode=record.drive_mode,
        )

        # Battery & Voltage
        self.battery_widget.set_battery_data(
            record.battery_soc, record.battery_voltage, record.battery_current
        )
        self.amp_val.setText(f"{record.battery_current:+.1f} A")

        # Power & Regen
        self.power_val.setText(f"{record.battery_power_kw:+.1f} kW")
        if record.battery_power_kw < -0.5:
            self.power_val.setStyleSheet("color: #10B981;")  # Green for Regen
        elif record.battery_power_kw > 60.0:
            self.power_val.setStyleSheet("color: #F59E0B;")  # Amber for High Load
        else:
            self.power_val.setStyleSheet("color: #00F0FF;")  # Cyan for Normal

        self.power_bar.set_power(record.battery_power_kw)

        # Pedals
        self.throttle_label.setText(f"THR: {int(record.throttle_pct)}%")
        self.brake_label.setText(f"BRK: {int(record.brake_pct)}%")

        # Drive Mode badge
        self.mode_badge.setText(record.drive_mode)
        if record.drive_mode == "SPORT":
            self.mode_badge.setStyleSheet(
                "background-color: rgba(239, 68, 68, 0.2); color: #F87171; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.5); font-weight: bold;"
            )
        elif record.drive_mode == "ECO":
            self.mode_badge.setStyleSheet(
                "background-color: rgba(16, 185, 129, 0.2); color: #34D399; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.5); font-weight: bold;"
            )
        else:
            self.mode_badge.setStyleSheet(
                "background-color: rgba(59, 130, 246, 0.2); color: #60A5FA; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(59, 130, 246, 0.5); font-weight: bold;"
            )

        # Warnings / Status
        if record.warnings:
            warn_text = " | ".join(record.warnings)
            self.status_badge.setText(f"⚠️ {warn_text}")
            self.status_badge.setStyleSheet(
                "background-color: rgba(239, 68, 68, 0.25); color: #FCA5A5; padding: 2px 10px; border-radius: 4px; border: 1px solid #EF4444; font-weight: bold;"
            )
        else:
            self.status_badge.setText("SYSTEM READY")
            self.status_badge.setStyleSheet(
                "background-color: rgba(16, 185, 129, 0.12); color: #34D399; padding: 2px 10px; border-radius: 4px;"
            )

        # Thermals
        self.thermal_widget.set_temperatures(
            record.motor_temp_c, record.inverter_temp_c, record.battery_temp_c
        )

        # Trip Odometer
        self.trip_dist_val.setText(f"{record.trip_distance_km:.2f} km")

        # Sparkline trace
        self.sparkline_widget.add_data_point(record.speed_kmh, record.battery_power_kw)

    def keyPressEvent(self, event) -> None:
        """Keyboard controls for bench testing on development workstations."""
        key = event.key()
        if key in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()
        elif key == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif key == Qt.Key.Key_M:
            self.drive_mode_requested.emit()
        elif key == Qt.Key.Key_Space:
            self.pause_requested.emit()
        else:
            super().keyPressEvent(event)
