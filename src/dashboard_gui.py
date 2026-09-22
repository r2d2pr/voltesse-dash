"""
Voltesse Dash - Modern Automotive Digital Cockpit GUI
A sleek, compact, distraction-free instrument cluster engineered for embedded
in-vehicle displays (e.g. Raspberry Pi automotive HUD / cluster screens).
Features a high-contrast Cyber-Mint aesthetic with responsive, unclipped typography.
"""

from collections import deque
import math
import time
from typing import Deque, List, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.database import TelemetryRecord


# =====================================================================
# Modern Cyber-Mint Automotive Color Palette
# =====================================================================
COLOR_BG_DARK = QColor("#030706")
COLOR_PANEL_BG = QColor(8, 18, 14, 230)
COLOR_PANEL_BORDER = QColor(18, 50, 38, 200)

# Mint Green Spectrum
COLOR_MINT = QColor("#00F5A0")           # Primary Neon Mint
COLOR_MINT_BRIGHT = QColor("#5CFFC7")    # Highlight Mint
COLOR_MINT_DIM = QColor(0, 245, 160, 45) # Subtle glow
COLOR_MINT_DARK = QColor("#00B374")      # Deep Mint / Emerald

# Secondary Accents
COLOR_AMBER = QColor("#FFB800")          # High Load / Warning
COLOR_RED = QColor("#FF4D6D")            # Critical / Brake Coral Red
COLOR_TEXT_PRIMARY = QColor("#FFFFFF")   # Pure White Readouts
COLOR_TEXT_SECONDARY = QColor("#9AE6B4") # Soft Mint / Sage Text
COLOR_TEXT_MUTED = QColor("#4E7566")     # Low-profile Muted Mints
COLOR_GAUGE_TRACK = QColor(12, 26, 20, 230)
COLOR_GAUGE_ACCENT = QColor(20, 44, 34, 240)


class SpeedometerDialWidget(QWidget):
    """
    Sleek automotive central speedometer with generous spacing and unclipped typography.
    Features inward graduation ticks, glowing mint sweep,
    crisp digital speed numerals, an automotive capsule gear selector, and bottom dual pedal dynamics.
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

        # Safe margins preventing any widget border clipping
        padding = 16.0
        outer_r = (side / 2.0) - padding
        track_r = outer_r - 10.0
        track_w = max(6.0, side * 0.030)

        # Arc Angles: 225 deg start (bottom-left), 270 deg clockwise sweep
        start_angle_deg = 225.0
        total_span_deg = -270.0

        # 1. Subtle Ambient Mint Glow Ring
        glow_grad = QRadialGradient(QPointF(cx, cy), track_r + 14)
        glow_grad.setColorAt(0.68, QColor(0, 0, 0, 0))
        glow_grad.setColorAt(0.88, COLOR_MINT_DIM)
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), track_r + 14, track_r + 14)

        # 2. Main Gauge Track (Dark Smoked Mint)
        gauge_rect = QRectF(cx - track_r, cy - track_r, track_r * 2, track_r * 2)
        pen_track = QPen(COLOR_GAUGE_TRACK, track_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_track)
        painter.drawArc(gauge_rect, int(start_angle_deg * 16), int(total_span_deg * 16))

        # 3. Precision Graduation Ticks & Numbers (Inward layout with wide clearance)
        num_ticks = 19  # Every 10 km/h from 0 to 180
        for i in range(num_ticks):
            val = i * 10
            fraction = i / (num_ticks - 1)
            angle_deg = start_angle_deg + (total_span_deg * fraction)
            rad = math.radians(-angle_deg)

            is_major = (i % 3 == 0)  # 0, 30, 60, 90, 120, 150, 180
            tick_len = side * (0.036 if is_major else 0.018)
            tick_width = 2.0 if is_major else 1.0

            # Tick lines pointing inward
            r_outer = track_r - (track_w / 2.0) - 2.0
            r_inner = r_outer - tick_len
            x1 = cx + math.cos(rad) * r_outer
            y1 = cy + math.sin(rad) * r_outer
            x2 = cx + math.cos(rad) * r_inner
            y2 = cy + math.sin(rad) * r_inner

            is_active = fraction <= (self.current_val / self.max_val)
            if is_active:
                tick_color = COLOR_MINT if fraction < 0.75 else COLOR_AMBER
            else:
                tick_color = COLOR_TEXT_SECONDARY if is_major else COLOR_TEXT_MUTED

            painter.setPen(QPen(tick_color, tick_width))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Major Tick Numbers (Ample 40x22 rects placed safely inside tick radius)
            if is_major and side > 180:
                r_num = r_inner - (side * 0.055)
                nx = cx + math.cos(rad) * r_num
                ny = cy + math.sin(rad) * r_num

                num_color = COLOR_MINT if is_active else COLOR_TEXT_MUTED
                painter.setPen(num_color)
                font_tick = QFont("Segoe UI", max(8, int(side * 0.032)), QFont.Weight.Bold)
                painter.setFont(font_tick)
                painter.drawText(QRectF(nx - 20, ny - 11, 40, 22), Qt.AlignmentFlag.AlignCenter, str(val))

        # 4. Active Speed Glowing Ribbon
        fraction = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        active_span_deg = total_span_deg * fraction

        if fraction > 0.005:
            # Dynamic color: Neon Mint -> Bright Mint -> Warm Amber at top speed
            if fraction < 0.65:
                sweep_color = COLOR_MINT
            elif fraction < 0.85:
                sweep_color = COLOR_MINT_BRIGHT
            else:
                sweep_color = COLOR_AMBER

            pen_sweep = QPen(sweep_color, track_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
            painter.setPen(pen_sweep)
            painter.drawArc(gauge_rect, int(start_angle_deg * 16), int(active_span_deg * 16))

            # Glowing needle tip beacon
            tip_angle = start_angle_deg + active_span_deg
            tip_rad = math.radians(-tip_angle)
            tip_x = cx + math.cos(tip_rad) * track_r
            tip_y = cy + math.sin(tip_rad) * track_r

            painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
            painter.setPen(QPen(sweep_color, 2))
            painter.drawEllipse(QPointF(tip_x, tip_y), 4.0, 4.0)

        # 5. Inner Concentric Ring
        inner_r = track_r - (side * 0.16)
        pen_inner = QPen(QColor(18, 50, 38, 120), 1.0, Qt.PenStyle.DashLine)
        painter.setPen(pen_inner)
        painter.drawArc(
            QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2),
            int(start_angle_deg * 16),
            int(total_span_deg * 16),
        )

        # 6. Central Large Digital Speedometer Readout (Generous unclipped bounding box)
        speed_int = int(round(self.current_val))
        font_speed_size = max(26, int(side * 0.19))
        font_speed = QFont("Segoe UI", font_speed_size, QFont.Weight.Bold)
        painter.setFont(font_speed)
        painter.setPen(COLOR_TEXT_PRIMARY)

        speed_box_w = side * 0.70
        speed_box_h = side * 0.30
        speed_rect = QRectF(cx - (speed_box_w / 2.0), cy - side * 0.22, speed_box_w, speed_box_h)
        painter.drawText(speed_rect, Qt.AlignmentFlag.AlignCenter, f"{speed_int}")

        # 7. Speed Unit Label
        painter.setPen(COLOR_MINT)
        font_unit = QFont("Segoe UI", max(9, int(side * 0.040)), QFont.Weight.Bold)
        font_unit.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(font_unit)
        unit_rect = QRectF(cx - 50, cy + side * 0.04, 100, 20)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, self.unit)

        # 8. Modern Automotive PRND Gear Selector Capsule
        gear_y = cy + side * 0.12
        gears = ["P", "R", "N", "D", "B"]
        slot_w = max(26.0, min(32.0, side * 0.075))
        box_h = max(24.0, min(28.0, side * 0.070))
        total_gear_w = len(gears) * slot_w
        start_gx = cx - (total_gear_w / 2.0)

        # Capsule background tray
        capsule_rect = QRectF(start_gx - 4, gear_y - 2, total_gear_w + 8, box_h + 4)
        painter.setBrush(QBrush(QColor(6, 14, 10, 180)))
        painter.setPen(QPen(QColor(18, 50, 38, 140), 1))
        painter.drawRoundedRect(capsule_rect, 6, 6)

        font_gear = QFont("Segoe UI", max(9, int(side * 0.034)), QFont.Weight.Bold)
        painter.setFont(font_gear)

        for idx, g in enumerate(gears):
            gx = start_gx + idx * slot_w
            slot_rect = QRectF(gx, gear_y, slot_w, box_h)

            if g == self.active_gear:
                active_pill = QRectF(gx + 2, gear_y + 1, slot_w - 4, box_h - 2)
                painter.setBrush(QBrush(QColor(0, 245, 160, 45)))
                painter.setPen(QPen(COLOR_MINT, 1.5))
                painter.drawRoundedRect(active_pill, 4, 4)
                painter.setPen(COLOR_TEXT_PRIMARY)
            else:
                painter.setPen(COLOR_TEXT_MUTED)

            painter.drawText(slot_rect, Qt.AlignmentFlag.AlignCenter, g)

        # RPM Subtitle
        painter.setPen(COLOR_TEXT_SECONDARY)
        font_rpm = QFont("Consolas", max(9, int(side * 0.033)), QFont.Weight.Normal)
        painter.setFont(font_rpm)
        rpm_rect = QRectF(cx - 80, cy + side * 0.21, 160, 20)
        painter.drawText(rpm_rect, Qt.AlignmentFlag.AlignCenter, f"{self.sub_val_label} {self.sub_val}")

        # 9. Dual Horizontal Micro-Meters for Throttle & Brake (Sleek bottom placement)
        pedal_y = cy + side * 0.29
        bar_w = min(50.0, side * 0.16)
        bar_h = 4.5

        # Brake Micro-Meter (Left side)
        brk_bx = cx - bar_w - 18.0
        painter.setPen(COLOR_TEXT_MUTED)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(brk_bx - 26, pedal_y - 4, 22, 12), Qt.AlignmentFlag.AlignRight, "BRK")

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(brk_bx, pedal_y, bar_w, bar_h), 2, 2)
        brk_fill = bar_w * (min(100.0, self.brake_pct) / 100.0)
        if brk_fill > 0:
            painter.setBrush(QBrush(COLOR_RED))
            painter.drawRoundedRect(QRectF(brk_bx + bar_w - brk_fill, pedal_y, brk_fill, bar_h), 2, 2)

        # Throttle Micro-Meter (Right side)
        thr_bx = cx + 18.0
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(thr_bx, pedal_y, bar_w, bar_h), 2, 2)
        thr_fill = bar_w * (min(100.0, self.throttle_pct) / 100.0)
        if thr_fill > 0:
            painter.setBrush(QBrush(COLOR_MINT))
            painter.drawRoundedRect(QRectF(thr_bx, pedal_y, thr_fill, bar_h), 2, 2)

        painter.setPen(COLOR_TEXT_MUTED)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(thr_bx + bar_w + 4, pedal_y - 4, 22, 12), Qt.AlignmentFlag.AlignLeft, "THR")

        painter.end()


# Alias for backward compatibility
ArcGaugeWidget = SpeedometerDialWidget


class BatteryStatusWidget(QWidget):
    """
    Sleek automotive left-wing hero module:
    Cyber-Mint Battery SoC arc and prominent estimated range HUD
    inside a dark smoked glass pod, positioned directly below the Energy & Battery header.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.soc = 100.0
        self.voltage = 400.0
        self.current = 0.0
        self.est_range_km = 340.0
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(88)

    def set_battery_data(self, soc: float, voltage: float, current: float) -> None:
        self.soc = max(0.0, min(100.0, soc))
        self.voltage = voltage
        self.current = current
        self.est_range_km = self.soc * 4.2
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

        # Smoked Glass Card Container
        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 5, 5)

        # Dynamic Battery Theme Color
        if self.soc > 30.0:
            bar_color = COLOR_MINT
        elif self.soc > 15.0:
            bar_color = COLOR_AMBER
        else:
            bar_color = COLOR_RED

        # 1. Swept Battery Arc
        arc_r = 34.0
        arc_cx = arc_r + 14.0
        arc_cy = h / 2.0
        arc_rect = QRectF(arc_cx - arc_r, arc_cy - arc_r, arc_r * 2, arc_r * 2)

        start_ang = 210.0
        span_ang = -240.0
        pen_track = QPen(COLOR_GAUGE_TRACK, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_track)
        painter.drawArc(arc_rect, int(start_ang * 16), int(span_ang * 16))

        active_span = span_ang * (self.soc / 100.0)
        if self.soc > 0.5:
            pen_active = QPen(bar_color, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_active)
            painter.drawArc(arc_rect, int(start_ang * 16), int(active_span * 16))

        # SoC Percentage Digits inside Arc
        painter.setPen(COLOR_TEXT_PRIMARY)
        font_soc = QFont("Segoe UI", 13, QFont.Weight.Bold)
        painter.setFont(font_soc)
        painter.drawText(QRectF(arc_cx - arc_r + 4, arc_cy - 14, (arc_r - 4) * 2, 28), Qt.AlignmentFlag.AlignCenter, f"{int(round(self.soc))}%")

        # 2. Prominent Estimated Range Readout
        range_x = arc_cx + arc_r + 16.0
        range_w = max(60.0, w - range_x - 8.0)

        painter.setPen(COLOR_TEXT_MUTED)
        font_sub = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(font_sub)
        painter.drawText(QRectF(range_x, arc_cy - 20, range_w, 16), Qt.AlignmentFlag.AlignLeft, "EST. RANGE")

        painter.setPen(COLOR_MINT)
        font_range = QFont("Segoe UI", 18, QFont.Weight.Bold)
        painter.setFont(font_range)
        painter.drawText(QRectF(range_x, arc_cy - 4, range_w, 26), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{int(self.est_range_km)} km")

        painter.end()


class TPMSWidget(QWidget):
    """
    4-Wheel Tire Pressure and Temperature Monitor (TPMS) Pod.
    Renders a top-down EV chassis schematic flanked by real-time corner readouts.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.fl_bar = 2.40
        self.fr_bar = 2.40
        self.rl_bar = 2.38
        self.rr_bar = 2.38
        self.fl_temp = 31.0
        self.fr_temp = 31.0
        self.rl_temp = 30.0
        self.rr_temp = 30.0
        self.setFixedHeight(78)

    def set_tpms(
        self,
        fl_bar: float,
        fr_bar: float,
        rl_bar: float,
        rr_bar: float,
        fl_temp: float,
        fr_temp: float,
        rl_temp: float,
        rr_temp: float,
    ) -> None:
        self.fl_bar = fl_bar
        self.fr_bar = fr_bar
        self.rl_bar = rl_bar
        self.rr_bar = rr_bar
        self.fl_temp = fl_temp
        self.fr_temp = fr_temp
        self.rl_temp = rl_temp
        self.rr_temp = rr_temp
        self.update()

    def _color_for_bar(self, bar: float) -> QColor:
        if bar < 2.0 or bar > 2.85:
            return COLOR_RED
        elif bar < 2.2 or bar > 2.65:
            return COLOR_AMBER
        return COLOR_MINT

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

        # Smoked Card Container
        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 5, 5)

        # Header Strip
        painter.setPen(COLOR_TEXT_MUTED)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(10, 4, w - 20, 14), Qt.AlignmentFlag.AlignLeft, "TIRE PRESSURE & TPMS")

        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(10, 4, w - 20, 14), Qt.AlignmentFlag.AlignRight, "● ALL NOMINAL")

        # Center Vehicle Chassis Silhouette
        cx = w / 2.0
        cy = 44.0

        # Chassis outline
        cw, ch = 24.0, 40.0
        chassis_rect = QRectF(cx - cw / 2.0, cy - ch / 2.0, cw, ch)
        painter.setBrush(QBrush(QColor(12, 30, 22, 220)))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1.2))
        painter.drawRoundedRect(chassis_rect, 6, 6)

        # Windshield accent
        painter.setPen(QPen(QColor(0, 245, 160, 60), 1))
        painter.drawLine(int(cx - 8), int(cy - 6), int(cx + 8), int(cy - 6))

        # 4 Wheels (Small rounded glowing blocks)
        tw, th = 5.0, 10.0
        wheel_coords = [
            (cx - 15.0, cy - 15.0, self.fl_bar),  # FL
            (cx + 10.0, cy - 15.0, self.fr_bar),  # FR
            (cx - 15.0, cy + 5.0, self.rl_bar),   # RL
            (cx + 10.0, cy + 5.0, self.rr_bar),   # RR
        ]
        for wx, wy, p_val in wheel_coords:
            painter.setBrush(QBrush(self._color_for_bar(p_val)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(wx, wy, tw, th), 1.5, 1.5)

        # Tire Readouts (Left Side: FL & RL)
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        left_col_w = cx - 22.0

        # FL Readout
        painter.setPen(self._color_for_bar(self.fl_bar))
        painter.drawText(QRectF(8, cy - 18, left_col_w, 14), Qt.AlignmentFlag.AlignLeft, f"FL {self.fl_bar:.2f} bar")
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(8, cy - 6, left_col_w, 12), Qt.AlignmentFlag.AlignLeft, f"{self.fl_temp:.0f}°C")

        # RL Readout
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(self._color_for_bar(self.rl_bar))
        painter.drawText(QRectF(8, cy + 8, left_col_w, 14), Qt.AlignmentFlag.AlignLeft, f"RL {self.rl_bar:.2f} bar")
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(8, cy + 20, left_col_w, 12), Qt.AlignmentFlag.AlignLeft, f"{self.rl_temp:.0f}°C")

        # Tire Readouts (Right Side: FR & RR)
        right_x = cx + 22.0
        right_col_w = w - right_x - 8.0

        # FR Readout
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(self._color_for_bar(self.fr_bar))
        painter.drawText(QRectF(right_x, cy - 18, right_col_w, 14), Qt.AlignmentFlag.AlignRight, f"{self.fr_bar:.2f} bar FR")
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(right_x, cy - 6, right_col_w, 12), Qt.AlignmentFlag.AlignRight, f"{self.fr_temp:.0f}°C")

        # RR Readout
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(self._color_for_bar(self.rr_bar))
        painter.drawText(QRectF(right_x, cy + 8, right_col_w, 14), Qt.AlignmentFlag.AlignRight, f"{self.rr_bar:.2f} bar RR")
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Normal))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(right_x, cy + 20, right_col_w, 12), Qt.AlignmentFlag.AlignRight, f"{self.rr_temp:.0f}°C")

        painter.end()


class AwdTorqueVectorWidget(QWidget):
    """
    Dual-Motor AWD Dynamic Torque Split & Vectoring Pod.
    Displays dynamic front/rear motor torque proportion bars and torque readouts in Nm.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.front_pct = 45.0
        self.rear_pct = 55.0
        self.front_nm = 0.0
        self.rear_nm = 0.0
        self.bias_mode = "AWD BALANCED"
        self.setFixedHeight(78)

    def set_torque_split(
        self,
        front_pct: float,
        rear_pct: float,
        front_nm: float,
        rear_nm: float,
        bias_mode: str = "AWD BALANCED",
    ) -> None:
        self.front_pct = front_pct
        self.rear_pct = rear_pct
        self.front_nm = front_nm
        self.rear_nm = rear_nm
        self.bias_mode = bias_mode
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

        # Smoked Card Container
        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 5, 5)

        # Header Strip
        painter.setPen(COLOR_TEXT_MUTED)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(10, 4, w - 20, 14), Qt.AlignmentFlag.AlignLeft, "AWD TORQUE VECTORING")

        painter.setPen(COLOR_MINT_BRIGHT)
        painter.drawText(QRectF(10, 4, w - 20, 14), Qt.AlignmentFlag.AlignRight, f"● {self.bias_mode}")

        # Geometry for Dual Motor Split Bars
        bar_left = 68.0
        bar_right = w - 85.0
        bar_w = max(40.0, bar_right - bar_left)
        bar_h = 7.0

        # Row 1: Front Motor (F-AXLE)
        y1 = 26.0
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(10, y1 - 4, 52, 14), Qt.AlignmentFlag.AlignLeft, "F-AXLE")

        # Track 1
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_left, y1, bar_w, bar_h), 2.5, 2.5)

        # Fill 1
        f_fill = bar_w * (self.front_pct / 100.0)
        painter.setBrush(QBrush(COLOR_MINT))
        painter.drawRoundedRect(QRectF(bar_left, y1, f_fill, bar_h), 2.5, 2.5)

        # Values 1
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(w - 80, y1 - 4, 72, 14), Qt.AlignmentFlag.AlignRight, f"{int(self.front_pct)}% {int(self.front_nm)}Nm")

        # Row 2: Rear Motor (R-AXLE)
        y2 = 49.0
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(10, y2 - 4, 52, 14), Qt.AlignmentFlag.AlignLeft, "R-AXLE")

        # Track 2
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_left, y2, bar_w, bar_h), 2.5, 2.5)

        # Fill 2
        r_fill = bar_w * (self.rear_pct / 100.0)
        r_color = COLOR_MINT_BRIGHT if self.rear_pct < 65.0 else COLOR_AMBER
        painter.setBrush(QBrush(r_color))
        painter.drawRoundedRect(QRectF(bar_left, y2, r_fill, bar_h), 2.5, 2.5)

        # Values 2
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(w - 80, y2 - 4, 72, 14), Qt.AlignmentFlag.AlignRight, f"{int(self.rear_pct)}% {int(self.rear_nm)}Nm")

        painter.end()


class PowerBarWidget(QWidget):
    """
    Sleek bidirectional power bar meter in Cyber-Mint theme.
    Regen (< 0 kW) on left in Mint Green; Discharge (> 0 kW) on right in Bright Mint / Amber.
    """

    def __init__(self, max_kw: float = 120.0, max_regen_kw: float = 60.0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.max_kw = max_kw
        self.max_regen_kw = max_regen_kw
        self.power_kw = 0.0
        self.setFixedHeight(24)

    def set_power(self, power_kw: float) -> None:
        self.power_kw = power_kw
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_h = 7.0
        y = (h - bar_h) / 2.0

        # Background track
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, y, w, bar_h), 3, 3)

        # Center split marker
        center_x = w * (self.max_regen_kw / (self.max_kw + self.max_regen_kw))
        painter.setPen(QPen(COLOR_TEXT_MUTED, 1.5))
        painter.drawLine(int(center_x), int(y - 2), int(center_x), int(y + bar_h + 2))

        # Active Fill
        if self.power_kw < -0.2:
            # Regen (leftwards in Mint Green)
            ratio = min(1.0, abs(self.power_kw) / self.max_regen_kw)
            fill_w = center_x * ratio
            fill_rect = QRectF(center_x - fill_w, y, fill_w, bar_h)
            painter.setBrush(QBrush(COLOR_MINT))
            painter.drawRoundedRect(fill_rect, 2, 2)
        elif self.power_kw > 0.2:
            # Discharge (rightwards)
            ratio = min(1.0, self.power_kw / self.max_kw)
            fill_w = (w - center_x) * ratio
            fill_rect = QRectF(center_x, y, fill_w, bar_h)
            color = COLOR_AMBER if self.power_kw > (self.max_kw * 0.7) else COLOR_MINT_BRIGHT
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(fill_rect, 2, 2)

        painter.end()


class LiveSparklineWidget(QWidget):
    """
    Real-time rolling oscilloscope telemetry wave in Cyber-Mint.
    """

    def __init__(self, max_points: int = 50, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.max_points = max_points
        self.speed_history: Deque[float] = deque(maxlen=max_points)
        self.power_history: Deque[float] = deque(maxlen=max_points)
        self.setFixedHeight(46)

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
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 5, 5)

        # Subtle oscilloscope grid lines
        painter.setPen(QPen(QColor(0, 245, 160, 15), 1, Qt.PenStyle.DotLine))
        painter.drawLine(0, int(h * 0.33), w, int(h * 0.33))
        painter.drawLine(0, int(h * 0.66), w, int(h * 0.66))

        count = len(self.speed_history)
        if count < 2:
            painter.end()
            return

        step_x = (w - 4) / (self.max_points - 1)

        # 1. Speed Trace (Glowing Mint)
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

        painter.setPen(QPen(COLOR_MINT, 1.8))
        painter.drawPath(speed_path)

        # 2. Power Trace (Amber)
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
        painter.setPen(COLOR_MINT)
        painter.drawText(8, 12, "SPD")
        painter.setPen(COLOR_AMBER)
        painter.drawText(36, 12, "PWR")

        painter.end()


class ThermalMonitorWidget(QWidget):
    """
    Powertrain Thermal Monitor (Motor, Inverter, Battery) in Cyber-Mint.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.motor_temp = 0.0
        self.inverter_temp = 0.0
        self.batt_temp = 0.0
        self.setFixedHeight(44)

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
        return COLOR_MINT

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
            painter.drawRoundedRect(QRectF(box_x, 0, box_w, 42), 5, 5)

            # Label
            painter.setPen(COLOR_TEXT_MUTED)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(box_x + 8, 3, box_w - 16, 14), Qt.AlignmentFlag.AlignLeft, label)

            # Value & Status pip
            painter.setPen(color)
            painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            painter.drawText(QRectF(box_x + 8, 18, box_w - 24, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{temp:.1f}°C")

            # Mini status indicator
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(box_x + box_w - 12, 28), 3.5, 3.5)

        painter.end()


class VoltesseDashboard(QMainWindow):
    """
    Main Automotive Digital Cockpit Cluster Window.
    Distraction-free, modern, sleek, high-contrast Cyber-Mint UI.
    Features perfectly leveled symmetrical left and right instrumentation wings.
    """

    drive_mode_requested = pyqtSignal()
    pause_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voltesse Dash - Digital Cockpit")
        self.setMinimumSize(960, 540)
        self.resize(1280, 720)

        # Style sheet (Cyber-Mint Dark Glass Automotive Cluster)
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #030706;
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
        main_layout.setSpacing(8)

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
        self.left_blinker.setStyleSheet("color: #123226;")

        # Brand / Subtitle
        brand_label = QLabel("⚡ VOLTESSE")
        brand_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Black))
        brand_label.setStyleSheet("color: #00F5A0; letter-spacing: 2px;")

        # Ready Indicator
        self.ready_badge = QLabel("READY")
        self.ready_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.ready_badge.setStyleSheet(
            "color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4);"
        )

        # Drive Mode Pill
        self.mode_badge = QLabel("DRIVE")
        self.mode_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.mode_badge.setStyleSheet(
            "background-color: rgba(0, 245, 160, 0.15); color: #5CFFC7; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4);"
        )

        # Status / Warning Pill
        self.status_badge = QLabel("SYSTEM READY")
        self.status_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.status_badge.setStyleSheet(
            "background-color: rgba(0, 245, 160, 0.12); color: #5CFFC7; padding: 2px 10px; border-radius: 4px;"
        )

        # Ambient Temp
        self.ambient_label = QLabel("22°C")
        self.ambient_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.ambient_label.setStyleSheet("color: #9AE6B4;")

        # Live Clock
        self.clock_label = QLabel("00:00:00")
        self.clock_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.clock_label.setStyleSheet("color: #FFFFFF;")

        # Turn Signal Right
        self.right_blinker = QLabel("►")
        self.right_blinker.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.right_blinker.setStyleSheet("color: #123226;")

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
        stage_layout.setSpacing(16)

        # =============================================================
        # --- LEFT WING: Energy & Battery + TPMS ---
        # =============================================================
        left_wing = QFrame()
        left_wing.setStyleSheet("background: transparent;")
        left_wing_layout = QVBoxLayout(left_wing)
        left_wing_layout.setContentsMargins(6, 2, 6, 2)
        left_wing_layout.setSpacing(6)

        # 1. Left Header (Pixel-perfect leveled with Right Header)
        left_hdr = QLabel("⚡ ENERGY & BATTERY")
        left_hdr.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        left_hdr.setFixedHeight(22)
        left_hdr.setStyleSheet("color: #9AE6B4; letter-spacing: 1px;")
        left_wing_layout.addWidget(left_hdr)

        # 2. Battery SoC Arc + Est. Range Card Pod (Directly below header)
        self.battery_widget = BatteryStatusWidget()
        left_wing_layout.addWidget(self.battery_widget)

        # 3. Compact Electrical Telemetry Capsule (Voltage & Current)
        volt_curr_pod = QFrame()
        volt_curr_pod.setFixedHeight(30)
        volt_curr_pod.setStyleSheet(
            "background-color: rgba(8, 18, 14, 0.9); border: 1px solid rgba(18, 50, 38, 0.8); border-radius: 5px;"
        )
        vc_layout = QHBoxLayout(volt_curr_pod)
        vc_layout.setContentsMargins(8, 0, 8, 0)

        v_lbl = QLabel("VOLT")
        v_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        v_lbl.setStyleSheet("color: #4E7566; border: none; background: transparent;")

        self.volt_val = QLabel("400.0 V")
        self.volt_val.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.volt_val.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")

        sep = QLabel("│")
        sep.setStyleSheet("color: rgba(18, 50, 38, 0.9); border: none; background: transparent;")

        c_lbl = QLabel("CURR")
        c_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        c_lbl.setStyleSheet("color: #4E7566; border: none; background: transparent;")

        self.amp_val = QLabel("+0.0 A")
        self.amp_val.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.amp_val.setStyleSheet("color: #00F5A0; border: none; background: transparent;")

        vc_layout.addWidget(v_lbl)
        vc_layout.addWidget(self.volt_val)
        vc_layout.addStretch(1)
        vc_layout.addWidget(sep)
        vc_layout.addStretch(1)
        vc_layout.addWidget(c_lbl)
        vc_layout.addWidget(self.amp_val)

        left_wing_layout.addWidget(volt_curr_pod)

        # 4. Energy Efficiency Deck Pod
        energy_pod = QFrame()
        energy_pod.setFixedHeight(46)
        energy_pod.setStyleSheet(
            "background-color: rgba(8, 18, 14, 0.9); border: 1px solid rgba(18, 50, 38, 0.8); border-radius: 5px;"
        )
        ep_layout = QVBoxLayout(energy_pod)
        ep_layout.setContentsMargins(10, 4, 10, 4)
        ep_layout.setSpacing(2)

        ep_top = QHBoxLayout()
        ep_hdr = QLabel("EFFICIENCY")
        ep_hdr.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        ep_hdr.setStyleSheet("color: #4E7566; border: none; background: transparent;")
        self.eff_val = QLabel("15.2 kWh/100km")
        self.eff_val.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.eff_val.setStyleSheet("color: #5CFFC7; border: none; background: transparent;")
        ep_top.addWidget(ep_hdr)
        ep_top.addStretch(1)
        ep_top.addWidget(self.eff_val)

        ep_bot = QHBoxLayout()
        hlth_hdr = QLabel("PACK HEALTH")
        hlth_hdr.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        hlth_hdr.setStyleSheet("color: #4E7566; border: none; background: transparent;")
        self.health_val = QLabel("100% NOMINAL")
        self.health_val.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.health_val.setStyleSheet("color: #00F5A0; border: none; background: transparent;")
        ep_bot.addWidget(hlth_hdr)
        ep_bot.addStretch(1)
        ep_bot.addWidget(self.health_val)

        ep_layout.addLayout(ep_top)
        ep_layout.addLayout(ep_bot)

        left_wing_layout.addWidget(energy_pod)

        # 5. 4-Wheel TPMS Monitoring Widget (Occupies lower left wing space)
        self.tpms_widget = TPMSWidget()
        left_wing_layout.addWidget(self.tpms_widget)
        left_wing_layout.addStretch(1)

        stage_layout.addWidget(left_wing, stretch=3)

        # =============================================================
        # --- CENTER STAGE: Primary Speedometer Dial ---
        # =============================================================
        center_stage = QFrame()
        center_stage.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center_stage)
        center_layout.setContentsMargins(0, 0, 0, 0)

        self.speed_gauge = SpeedometerDialWidget(min_val=0.0, max_val=180.0, title="SPEED", unit="KM/H")
        center_layout.addWidget(self.speed_gauge)

        stage_layout.addWidget(center_stage, stretch=4)

        # =============================================================
        # --- RIGHT WING: Powertrain Dynamics + AWD Vectoring ---
        # =============================================================
        right_wing = QFrame()
        right_wing.setStyleSheet("background: transparent;")
        right_wing_layout = QVBoxLayout(right_wing)
        right_wing_layout.setContentsMargins(6, 2, 6, 2)
        right_wing_layout.setSpacing(6)

        # 1. Right Header (Pixel-perfect leveled with Left Header)
        right_hdr = QLabel("⚡ POWERTRAIN DYNAMICS")
        right_hdr.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        right_hdr.setFixedHeight(22)
        right_hdr.setStyleSheet("color: #9AE6B4; letter-spacing: 1px;")
        right_wing_layout.addWidget(right_hdr)

        # 2. Net Power Pod
        power_pod = QFrame()
        power_pod.setStyleSheet("background-color: rgba(8, 18, 14, 0.9); border: 1px solid rgba(18, 50, 38, 0.8); border-radius: 5px;")
        power_pod_layout = QHBoxLayout(power_pod)
        power_pod_layout.setContentsMargins(10, 6, 10, 6)

        power_title = QLabel("NET POWER")
        power_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        power_title.setStyleSheet("color: #4E7566;")

        self.power_val = QLabel("0.0 kW")
        self.power_val.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        self.power_val.setStyleSheet("color: #00F5A0;")

        power_pod_layout.addWidget(power_title)
        power_pod_layout.addStretch(1)
        power_pod_layout.addWidget(self.power_val)
        right_wing_layout.addWidget(power_pod)

        # 3. Power / Regen Bar
        self.power_bar = PowerBarWidget()
        right_wing_layout.addWidget(self.power_bar)

        # 4. Dynamic Pedals Status Strip
        pedal_frame = QFrame()
        pedal_frame.setFixedHeight(24)
        pedal_layout = QHBoxLayout(pedal_frame)
        pedal_layout.setContentsMargins(0, 0, 0, 0)

        self.throttle_label = QLabel("THR: 0%")
        self.throttle_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.throttle_label.setStyleSheet("color: #00F5A0;")

        self.brake_label = QLabel("BRK: 0%")
        self.brake_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.brake_label.setStyleSheet("color: #FF4D6D;")

        pedal_layout.addWidget(self.throttle_label)
        pedal_layout.addStretch(1)
        pedal_layout.addWidget(self.brake_label)
        right_wing_layout.addWidget(pedal_frame)

        # 5. Live Waveform inside Right Wing
        self.sparkline_widget = LiveSparklineWidget(max_points=50)
        right_wing_layout.addWidget(self.sparkline_widget)

        # 6. AWD Dual-Motor Dynamic Torque Vectoring Pod (Occupies lower right wing space)
        self.awd_widget = AwdTorqueVectorWidget()
        right_wing_layout.addWidget(self.awd_widget)
        right_wing_layout.addStretch(1)

        stage_layout.addWidget(right_wing, stretch=3)

        main_layout.addLayout(stage_layout, stretch=4)

        # -------------------------------------------------------------
        # 3. BOTTOM TELEMETRY & TRIP DECK
        # -------------------------------------------------------------
        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(48)
        bottom_bar.setStyleSheet("background: transparent;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)

        # Unified Single-Pod Trip Odometer
        trip_pod = QFrame()
        trip_pod.setFixedHeight(44)
        trip_pod.setFixedWidth(140)
        trip_pod.setStyleSheet(
            "background-color: rgba(8, 18, 14, 0.9); border: 1px solid rgba(18, 50, 38, 0.8); border-radius: 5px;"
        )
        trip_layout = QVBoxLayout(trip_pod)
        trip_layout.setContentsMargins(8, 3, 8, 3)
        trip_layout.setSpacing(0)

        trip_hdr = QLabel("TRIP ODOMETER")
        trip_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        trip_hdr.setStyleSheet("color: #4E7566; border: none; background: transparent;")

        self.trip_dist_val = QLabel("0.00 km")
        self.trip_dist_val.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.trip_dist_val.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")

        trip_layout.addWidget(trip_hdr)
        trip_layout.addWidget(self.trip_dist_val)
        bottom_layout.addWidget(trip_pod)

        # Thermal Diagnostics Pods
        self.thermal_widget = ThermalMonitorWidget()
        bottom_layout.addWidget(self.thermal_widget, stretch=1)

        main_layout.addWidget(bottom_bar)

    def _update_clock(self) -> None:
        self.clock_label.setText(time.strftime("%H:%M:%S"))

    def update_telemetry(self, record: TelemetryRecord) -> None:
        """
        Non-blocking slot updating all telemetry gauges and HUD indicators.
        """
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
        self.volt_val.setText(f"{record.battery_voltage:.1f} V")
        self.amp_val.setText(f"{record.battery_current:+.1f} A")
        if record.battery_current < -0.5:
            self.amp_val.setStyleSheet("color: #00F5A0; border: none; background: transparent;")
        elif record.battery_current > 80.0:
            self.amp_val.setStyleSheet("color: #FFB800; border: none; background: transparent;")
        else:
            self.amp_val.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")

        # Power & Regen
        self.power_val.setText(f"{record.battery_power_kw:+.1f} kW")
        if record.battery_power_kw < -0.5:
            self.power_val.setStyleSheet("color: #00F5A0;")  # Mint for Regen
        elif record.battery_power_kw > 60.0:
            self.power_val.setStyleSheet("color: #FFB800;")  # Amber for High Load
        else:
            self.power_val.setStyleSheet("color: #5CFFC7;")  # Bright Mint for Cruise

        self.power_bar.set_power(record.battery_power_kw)

        # Pedals
        self.throttle_label.setText(f"THR: {int(record.throttle_pct)}%")
        self.brake_label.setText(f"BRK: {int(record.brake_pct)}%")

        # Drive Mode badge
        self.mode_badge.setText(record.drive_mode)
        if record.drive_mode == "SPORT":
            self.mode_badge.setStyleSheet(
                "background-color: rgba(255, 77, 109, 0.2); color: #FF4D6D; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(255, 77, 109, 0.5); font-weight: bold;"
            )
        elif record.drive_mode == "ECO":
            self.mode_badge.setStyleSheet(
                "background-color: rgba(0, 179, 116, 0.2); color: #5CFFC7; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(0, 179, 116, 0.5); font-weight: bold;"
            )
        else:
            self.mode_badge.setStyleSheet(
                "background-color: rgba(0, 245, 160, 0.15); color: #5CFFC7; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
            )

        # Warnings / Status
        if record.warnings:
            warn_text = " | ".join(record.warnings)
            self.status_badge.setText(f"⚠️ {warn_text}")
            self.status_badge.setStyleSheet(
                "background-color: rgba(255, 77, 109, 0.25); color: #FFA3B4; padding: 2px 10px; border-radius: 4px; border: 1px solid #FF4D6D; font-weight: bold;"
            )
        else:
            self.status_badge.setText("SYSTEM READY")
            self.status_badge.setStyleSheet(
                "background-color: rgba(0, 245, 160, 0.12); color: #5CFFC7; padding: 2px 10px; border-radius: 4px;"
            )

        # Thermals
        self.thermal_widget.set_temperatures(
            record.motor_temp_c, record.inverter_temp_c, record.battery_temp_c
        )

        # Trip Odometer
        self.trip_dist_val.setText(f"{record.trip_distance_km:.2f} km")

        # Sparkline trace
        self.sparkline_widget.add_data_point(record.speed_kmh, record.battery_power_kw)

        # Dynamic AWD Dual-Motor Torque Calculation
        if record.battery_power_kw < -0.5:
            # Under regenerative braking: front bias
            f_ratio = 0.60
            r_ratio = 0.40
            bias_str = "REGEN AWD"
            total_nm = abs(record.battery_power_kw) * 3.5
        elif record.drive_mode == "SPORT":
            f_ratio = 0.30
            r_ratio = 0.70
            bias_str = "RWD BIAS"
            total_nm = (record.throttle_pct / 100.0) * 480.0
        elif record.drive_mode == "ECO":
            f_ratio = 0.75
            r_ratio = 0.25
            bias_str = "FWD ECO"
            total_nm = (record.throttle_pct / 100.0) * 260.0
        else:
            f_ratio = 0.45
            r_ratio = 0.55
            bias_str = "AWD DUAL"
            total_nm = (record.throttle_pct / 100.0) * 380.0

        f_pct = round(f_ratio * 100.0)
        r_pct = 100.0 - f_pct
        f_nm = total_nm * f_ratio
        r_nm = total_nm * r_ratio
        self.awd_widget.set_torque_split(f_pct, r_pct, f_nm, r_nm, bias_str)

        # Dynamic TPMS (Warms up slightly with speed and continuous driving)
        temp_base = 28.0 + min(12.0, (record.speed_kmh / 180.0) * 7.0 + (record.trip_distance_km * 0.08))
        fl_t = temp_base + 1.2
        fr_t = temp_base + 0.8
        rl_t = temp_base - 0.4
        rr_t = temp_base - 0.6

        # Ideal pressure 2.40 bar + gentle thermal inflation
        fl_p = 2.40 + (fl_t - 25.0) * 0.004
        fr_p = 2.40 + (fr_t - 25.0) * 0.004
        rl_p = 2.38 + (rl_t - 25.0) * 0.004
        rr_p = 2.38 + (rr_t - 25.0) * 0.004
        self.tpms_widget.set_tpms(fl_p, fr_p, rl_p, rr_p, fl_t, fr_t, rl_t, rr_t)

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
