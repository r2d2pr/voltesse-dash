"""
Voltesse Dash - Modern Automotive Digital Cockpit GUI
A sleek, distraction-free instrument cluster engineered for embedded
in-vehicle displays (e.g. Raspberry Pi automotive HUD / cluster screens).
Features a high-contrast Cyber-Mint aesthetic with full auto-scaling to variable
fullscreen resolutions and interactive video-game simulation controls.
Supports Automatic (PRNDB with dynamic speed-based D1-D6 gear display)
and 6-Speed Sequential Manual (R, N, 1-6) transmissions.
"""

from collections import deque
import math
import time
from typing import Deque, List, Optional, Set

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
COLOR_CYAN = QColor("#00E5FF")           # Game Simulation Cyan
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
    Features inward graduation ticks, glowing mint sweep, crisp digital speed numerals,
    an automotive transmission gear hub (Auto PRNDB with active gear or Manual R/N/1-6),
    dual pedal dynamics, and a real-time steering wheel angle indicator.
    Auto-scales cleanly to any fullscreen resolution while preserving balanced proportions.
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
        self.steering_angle = 0.0
        self.active_gear = "D1"
        self.transmission_mode = "AUTO"  # "AUTO" or "MANUAL"
        self.drive_mode = "DRIVE"

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(240, 240)

    def set_units(self, unit: str = "KM/H", max_val: float = 180.0) -> None:
        self.unit = unit
        self.max_val = max_val
        self.update()

    def set_value(self, value: float, sub_val: str = "") -> None:
        self.current_val = max(self.min_val, min(self.max_val, value))
        if sub_val:
            self.sub_val = sub_val
        self.update()

    def set_pedals_and_gear(
        self,
        throttle: float,
        brake: float,
        gear: str = "D1",
        mode: str = "DRIVE",
        steering_angle: float = 0.0,
        transmission_mode: str = "AUTO",
    ) -> None:
        self.throttle_pct = throttle
        self.brake_pct = brake
        self.active_gear = gear
        self.drive_mode = mode
        self.steering_angle = steering_angle
        self.transmission_mode = transmission_mode
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

        padding = max(12.0, side * 0.05)
        outer_r = (side / 2.0) - padding
        track_r = outer_r - (side * 0.025)
        track_w = max(5.0, min(14.0, side * 0.030))

        start_angle_deg = 225.0
        total_span_deg = -270.0

        # 1. Card Container background
        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(4, 4, w - 8, h - 8), 10, 10)

        # 2. Ambient Mint Glow Ring
        glow_rad = track_r + max(8.0, side * 0.035)
        glow_grad = QRadialGradient(QPointF(cx, cy), glow_rad)
        glow_grad.setColorAt(0.68, QColor(0, 0, 0, 0))
        glow_grad.setColorAt(0.88, COLOR_MINT_DIM)
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), glow_rad, glow_rad)

        # 3. Main Gauge Track (Dark Smoked Mint)
        gauge_rect = QRectF(cx - track_r, cy - track_r, track_r * 2, track_r * 2)
        pen_track = QPen(COLOR_GAUGE_TRACK, track_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_track)
        painter.drawArc(gauge_rect, int(start_angle_deg * 16), int(total_span_deg * 16))

        # 4. Precision Graduation Ticks & Numbers
        num_ticks = 19 if self.max_val >= 150.0 else 13
        for i in range(num_ticks):
            val = int(round(i * (self.max_val / (num_ticks - 1))))
            fraction = i / (num_ticks - 1)
            angle_deg = start_angle_deg + (total_span_deg * fraction)
            rad = math.radians(-angle_deg)

            is_major = (i % 3 == 0) if num_ticks == 19 else (i % 2 == 0)
            tick_len = side * (0.038 if is_major else 0.020)
            tick_width = max(1.0, side * (0.005 if is_major else 0.003))

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

            # Major Tick Numbers
            if is_major and side > 160:
                r_num = r_inner - (side * 0.055)
                nx = cx + math.cos(rad) * r_num
                ny = cy + math.sin(rad) * r_num

                num_color = COLOR_MINT if is_active else COLOR_TEXT_MUTED
                painter.setPen(num_color)
                font_tick = QFont("Segoe UI", max(7, min(15, int(side * 0.030))), QFont.Weight.Bold)
                painter.setFont(font_tick)
                nw = max(30.0, side * 0.09)
                nh = max(16.0, side * 0.05)
                painter.drawText(QRectF(nx - (nw / 2), ny - (nh / 2), nw, nh), Qt.AlignmentFlag.AlignCenter, str(val))

        # 5. Active Speed Glowing Ribbon
        fraction = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        active_span_deg = total_span_deg * fraction

        if fraction > 0.005:
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

            beacon_r = max(3.0, min(8.0, side * 0.012))
            painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
            painter.setPen(QPen(sweep_color, 2))
            painter.drawEllipse(QPointF(tip_x, tip_y), beacon_r, beacon_r)

        # 6. Inner Concentric Ring
        inner_r = track_r - (side * 0.15)
        pen_inner = QPen(QColor(18, 50, 38, 120), 1.0, Qt.PenStyle.DashLine)
        painter.setPen(pen_inner)
        painter.drawArc(
            QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2),
            int(start_angle_deg * 16),
            int(total_span_deg * 16),
        )

        # 7. Central Large Digital Speedometer Readout
        speed_int = int(round(self.current_val))
        font_speed_size = max(28, min(76, int(side * 0.16)))
        font_speed = QFont("Segoe UI", font_speed_size, QFont.Weight.Bold)
        painter.setFont(font_speed)
        painter.setPen(COLOR_TEXT_PRIMARY)

        speed_box_w = side * 0.70
        speed_box_h = side * 0.28
        speed_rect = QRectF(cx - (speed_box_w / 2.0), cy - side * 0.23, speed_box_w, speed_box_h)
        painter.drawText(speed_rect, Qt.AlignmentFlag.AlignCenter, f"{speed_int}")

        # 8. Speed Unit Label
        painter.setPen(COLOR_MINT)
        font_unit = QFont("Segoe UI", max(9, min(18, int(side * 0.036))), QFont.Weight.Bold)
        font_unit.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(1, int(side * 0.005)))
        painter.setFont(font_unit)
        unit_rect = QRectF(cx - side * 0.20, cy + side * 0.025, side * 0.40, side * 0.065)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, self.unit)

        # 9. Modern Automotive Transmission Hub (Auto PRNDB with active gear or Manual R/N/1-6)
        gear_y = cy + side * 0.095
        if self.transmission_mode == "MANUAL":
            gears = ["R", "N", "1", "2", "3", "4", "5", "6"]
        else:
            gears = ["P", "R", "N", "D", "B"]

        slot_w = max(20.0, min(38.0, (side * 0.48) / len(gears)))
        box_h = max(19.0, min(32.0, side * 0.058))
        total_gear_w = len(gears) * slot_w
        start_gx = cx - (total_gear_w / 2.0)

        capsule_rect = QRectF(start_gx - 4, gear_y - 2, total_gear_w + 8, box_h + 4)
        painter.setBrush(QBrush(QColor(6, 14, 10, 200)))
        painter.setPen(QPen(QColor(18, 50, 38, 160), 1))
        painter.drawRoundedRect(capsule_rect, 6, 6)

        font_gear = QFont("Segoe UI", max(7, min(13, int(side * 0.028))), QFont.Weight.Bold)
        painter.setFont(font_gear)

        for idx, g in enumerate(gears):
            gx = start_gx + idx * slot_w
            slot_rect = QRectF(gx, gear_y, slot_w, box_h)

            is_active = False
            label_text = g
            if self.transmission_mode == "MANUAL":
                is_active = (g == self.active_gear)
            else:
                if self.active_gear.startswith("D"):
                    is_active = (g == "D")
                    if is_active and len(self.active_gear) > 1:
                        label_text = self.active_gear  # e.g. D1, D2, D3, D4, D5, D6
                else:
                    is_active = (g == self.active_gear)

            if is_active:
                active_pill = QRectF(gx + 1.5, gear_y + 1, slot_w - 3, box_h - 2)
                highlight_col = COLOR_CYAN if self.transmission_mode == "MANUAL" else COLOR_MINT
                painter.setBrush(QBrush(QColor(highlight_col.red(), highlight_col.green(), highlight_col.blue(), 55)))
                painter.setPen(QPen(highlight_col, 1.5))
                painter.drawRoundedRect(active_pill, 4, 4)
                painter.setPen(COLOR_TEXT_PRIMARY)
            else:
                painter.setPen(COLOR_TEXT_MUTED)

            painter.drawText(slot_rect, Qt.AlignmentFlag.AlignCenter, label_text)

        # Prominent Gear & Transmission Status Hub Pill directly beneath capsule
        trans_status_y = gear_y + box_h + 4
        if self.transmission_mode == "MANUAL":
            if self.active_gear.isdigit():
                display_gear = f"M{self.active_gear}"
                status_text = f"MANUAL  •  {display_gear} (GEAR {self.active_gear})"
            elif self.active_gear == "N":
                status_text = "MANUAL  •  NEUTRAL [N]"
            elif self.active_gear == "R":
                status_text = "MANUAL  •  REVERSE [R]"
            else:
                status_text = f"MANUAL  •  {self.active_gear}"
        else:
            if self.active_gear.startswith("D") and len(self.active_gear) > 1 and self.active_gear[1:].isdigit():
                gear_num = self.active_gear[1:]
                status_text = f"AUTO  •  {self.active_gear} (GEAR {gear_num})"
            elif self.active_gear == "P":
                status_text = "AUTO  •  PARK [P]"
            elif self.active_gear == "R":
                status_text = "AUTO  •  REVERSE [R]"
            elif self.active_gear == "N":
                status_text = "AUTO  •  NEUTRAL [N]"
            elif self.active_gear == "B":
                status_text = "AUTO  •  REGEN [B]"
            else:
                status_text = f"AUTO  •  {self.active_gear}"

        painter.setPen(COLOR_CYAN if self.transmission_mode == "MANUAL" else COLOR_MINT_BRIGHT)
        font_status = QFont("Segoe UI", max(8, min(13, int(side * 0.026))), QFont.Weight.Bold)
        font_status.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        painter.setFont(font_status)
        painter.drawText(QRectF(cx - 110, trans_status_y, 220, 16), Qt.AlignmentFlag.AlignCenter, status_text)

        # RPM Subtitle
        painter.setPen(COLOR_TEXT_SECONDARY)
        font_rpm = QFont("Consolas", max(8, min(15, int(side * 0.026))), QFont.Weight.Normal)
        painter.setFont(font_rpm)
        rpm_rect = QRectF(cx - side * 0.30, cy + side * 0.19, side * 0.60, side * 0.055)
        painter.drawText(rpm_rect, Qt.AlignmentFlag.AlignCenter, f"{self.sub_val_label} {self.sub_val}")

        # 10. Dual Horizontal Micro-Meters for Throttle & Brake
        pedal_y = cy + side * 0.255
        bar_w = max(45.0, min(110.0, side * 0.16))
        bar_h = max(4.0, min(8.0, side * 0.015))

        # Brake Micro-Meter (Left side)
        brk_bx = cx - bar_w - (side * 0.04)
        painter.setPen(COLOR_TEXT_MUTED)
        painter.setFont(QFont("Segoe UI", max(6, min(11, int(side * 0.022))), QFont.Weight.Bold))
        painter.drawText(QRectF(brk_bx - 36, pedal_y - 4, 32, 14), Qt.AlignmentFlag.AlignRight, "BRK")

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(brk_bx, pedal_y, bar_w, bar_h), 2, 2)
        brk_fill = bar_w * (min(100.0, self.brake_pct) / 100.0)
        if brk_fill > 0:
            painter.setBrush(QBrush(COLOR_RED))
            painter.drawRoundedRect(QRectF(brk_bx + bar_w - brk_fill, pedal_y, brk_fill, bar_h), 2, 2)

        # Throttle Micro-Meter (Right side)
        thr_bx = cx + (side * 0.04)
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(thr_bx, pedal_y, bar_w, bar_h), 2, 2)
        thr_fill = bar_w * (min(100.0, self.throttle_pct) / 100.0)
        if thr_fill > 0:
            painter.setBrush(QBrush(COLOR_MINT))
            painter.drawRoundedRect(QRectF(thr_bx, pedal_y, thr_fill, bar_h), 2, 2)

        painter.setPen(COLOR_TEXT_MUTED)
        painter.setFont(QFont("Segoe UI", max(6, min(11, int(side * 0.022))), QFont.Weight.Bold))
        painter.drawText(QRectF(thr_bx + bar_w + 4, pedal_y - 4, 32, 14), Qt.AlignmentFlag.AlignLeft, "THR")

        # 11. Center Steering Wheel Angle Indicator
        steer_y = cy + side * 0.315
        angle = self.steering_angle
        steer_txt = f"STR ◄ {abs(int(angle))}°" if angle < -0.5 else (f"STR {int(angle)}° ►" if angle > 0.5 else "STR 0°")
        s_color = COLOR_CYAN if abs(angle) > 1.0 else COLOR_TEXT_MUTED

        painter.setPen(s_color)
        painter.setFont(QFont("Segoe UI", max(7, min(13, int(side * 0.024))), QFont.Weight.Bold))
        painter.drawText(QRectF(cx - 50, steer_y, 100, 16), Qt.AlignmentFlag.AlignCenter, steer_txt)

        painter.end()


# Alias for backward compatibility
ArcGaugeWidget = SpeedometerDialWidget


class BatteryStatusWidget(QWidget):
    """
    Sleek automotive left-wing hero module:
    Cyber-Mint Battery SoC arc, prominent estimated range HUD,
    and integrated electrical diagnostics in a balanced card pod.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.soc = 100.0
        self.voltage = 400.0
        self.current = 0.0
        self.est_range_km = 340.0
        self.unit_system = "METRIC"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(140)

    def set_unit_system(self, unit_system: str) -> None:
        self.unit_system = unit_system
        self.update()

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

        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 8, 8)

        hdr_font_sz = max(7, min(11, int(w * 0.026)))
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(14, 8, w - 28, 18), Qt.AlignmentFlag.AlignLeft, "⚡ ENERGY & BATTERY")

        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(14, 8, w - 28, 18), Qt.AlignmentFlag.AlignRight, "● PACK NOMINAL")

        if self.soc > 30.0:
            bar_color = COLOR_MINT
        elif self.soc > 15.0:
            bar_color = COLOR_AMBER
        else:
            bar_color = COLOR_RED

        card_content_h = h - 30.0
        arc_r = min(w * 0.18, card_content_h * 0.38)
        arc_cx = arc_r + 18.0
        arc_cy = 28.0 + (card_content_h * 0.42)
        arc_rect = QRectF(arc_cx - arc_r, arc_cy - arc_r, arc_r * 2, arc_r * 2)

        start_ang = 210.0
        span_ang = -240.0
        pen_w = max(4.0, min(9.0, arc_r * 0.18))
        pen_track = QPen(COLOR_GAUGE_TRACK, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_track)
        painter.drawArc(arc_rect, int(start_ang * 16), int(span_ang * 16))

        active_span = span_ang * (self.soc / 100.0)
        if self.soc > 0.5:
            pen_active = QPen(bar_color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_active)
            painter.drawArc(arc_rect, int(start_ang * 16), int(active_span * 16))

        painter.setPen(COLOR_TEXT_PRIMARY)
        font_soc_sz = max(9, min(22, int(arc_r * 0.38)))
        font_soc = QFont("Segoe UI", font_soc_sz, QFont.Weight.Bold)
        painter.setFont(font_soc)
        painter.drawText(
            QRectF(arc_cx - arc_r + 2, arc_cy - arc_r * 0.5, (arc_r - 2) * 2, arc_r),
            Qt.AlignmentFlag.AlignCenter,
            f"{int(round(self.soc))}%",
        )

        range_x = arc_cx + arc_r + 16.0
        range_w = max(60.0, w - range_x - 12.0)

        painter.setPen(COLOR_TEXT_MUTED)
        font_sub_sz = max(7, min(11, int(card_content_h * 0.09)))
        font_sub = QFont("Segoe UI", font_sub_sz, QFont.Weight.DemiBold)
        painter.setFont(font_sub)
        painter.drawText(
            QRectF(range_x, arc_cy - (card_content_h * 0.30), range_w, card_content_h * 0.22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "EST. RANGE",
        )

        painter.setPen(COLOR_MINT)
        font_range_sz = max(13, min(26, int(card_content_h * 0.20)))
        font_range = QFont("Segoe UI", font_range_sz, QFont.Weight.Bold)
        painter.setFont(font_range)
        if getattr(self, "unit_system", "METRIC") == "IMPERIAL":
            range_val = int(round(self.est_range_km * 0.621371))
            range_text = f"{range_val} mi"
        else:
            range_text = f"{int(round(self.est_range_km))} km"
        painter.drawText(
            QRectF(range_x, arc_cy - (card_content_h * 0.05), range_w, card_content_h * 0.32),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            range_text,
        )

        sub_y = h - max(32.0, h * 0.24)
        sub_h = h - sub_y - 8.0
        sub_rect = QRectF(12, sub_y, w - 24, sub_h)
        painter.setBrush(QBrush(QColor(6, 14, 10, 190)))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
        painter.drawRoundedRect(sub_rect, 4, 4)

        font_pod_lbl = QFont("Segoe UI", max(6, min(9, int(sub_h * 0.28))), QFont.Weight.Bold)
        font_pod_val = QFont("Consolas", max(7, min(12, int(sub_h * 0.40))), QFont.Weight.Bold)

        half_w = (w - 24) / 2.0
        painter.setFont(font_pod_lbl)
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(18, sub_y + 2, 40, sub_h - 4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "VOLT")
        painter.setFont(font_pod_val)
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(QRectF(58, sub_y + 2, half_w - 50, sub_h - 4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{self.voltage:.1f} V")

        rx = 12 + half_w
        painter.setFont(font_pod_lbl)
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(rx + 6, sub_y + 2, 40, sub_h - 4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "CURR")
        painter.setFont(font_pod_val)
        c_color = COLOR_MINT if self.current < -0.5 else (COLOR_AMBER if self.current > 70.0 else COLOR_TEXT_PRIMARY)
        painter.setPen(c_color)
        painter.drawText(QRectF(rx + 46, sub_y + 2, half_w - 52, sub_h - 4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{self.current:+.1f} A")

        painter.end()


class TPMSWidget(QWidget):
    """
    4-Wheel Tire Pressure and Temperature Monitor (TPMS) Pod.
    Renders a top-down EV chassis schematic flanked by real-time corner readouts.
    Auto-scales with correct car proportions across all resolutions.
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
        self.unit_system = "METRIC"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(140)

    def set_unit_system(self, unit_system: str) -> None:
        self.unit_system = unit_system
        self.update()

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

        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 8, 8)

        hdr_font_sz = max(7, min(11, int(w * 0.026)))
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(14, 8, w - 28, 18), Qt.AlignmentFlag.AlignLeft, "TIRE PRESSURE & TPMS")

        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(14, 8, w - 28, 18), Qt.AlignmentFlag.AlignRight, "● ALL NOMINAL")

        cx = w / 2.0
        cy = 28.0 + (h - 28.0) / 2.0

        content_h = h - 36.0
        ch = max(38.0, min(110.0, content_h * 0.58))
        cw = max(24.0, min(65.0, ch * 0.60))

        chassis_rect = QRectF(cx - cw / 2.0, cy - ch / 2.0, cw, ch)
        painter.setBrush(QBrush(QColor(12, 30, 22, 220)))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1.2))
        painter.drawRoundedRect(chassis_rect, 6, 6)

        painter.setPen(QPen(QColor(0, 245, 160, 70), 1))
        painter.drawLine(int(cx - cw * 0.35), int(cy - ch * 0.16), int(cx + cw * 0.35), int(cy - ch * 0.16))

        tw = max(4.0, min(10.0, cw * 0.22))
        th = max(7.0, min(20.0, ch * 0.25))
        wheel_dx = cw * 0.58
        wheel_dy = ch * 0.28
        wheel_coords = [
            (cx - wheel_dx - tw, cy - wheel_dy - th / 2, self.fl_bar),
            (cx + wheel_dx, cy - wheel_dy - th / 2, self.fr_bar),
            (cx - wheel_dx - tw, cy + wheel_dy - th / 2, self.rl_bar),
            (cx + wheel_dx, cy + wheel_dy - th / 2, self.rr_bar),
        ]
        for wx, wy, p_val in wheel_coords:
            painter.setBrush(QBrush(self._color_for_bar(p_val)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(wx, wy, tw, th), 2, 2)

        font_bar_sz = max(7, min(13, int(content_h * 0.10)))
        font_temp_sz = max(6, min(11, int(content_h * 0.08)))
        left_col_w = max(40.0, cx - wheel_dx - tw - 16.0)

        is_imp = (getattr(self, "unit_system", "METRIC") == "IMPERIAL")
        if is_imp:
            fl_p_str = f"FL {self.fl_bar * 14.5038:.1f}psi"
            rl_p_str = f"RL {self.rl_bar * 14.5038:.1f}psi"
            fr_p_str = f"{self.fr_bar * 14.5038:.1f}psi FR"
            rr_p_str = f"{self.rr_bar * 14.5038:.1f}psi RR"
            fl_t_str = f"{self.fl_temp * 9.0 / 5.0 + 32.0:.0f}°F"
            rl_t_str = f"{self.rl_temp * 9.0 / 5.0 + 32.0:.0f}°F"
            fr_t_str = f"{self.fr_temp * 9.0 / 5.0 + 32.0:.0f}°F"
            rr_t_str = f"{self.rr_temp * 9.0 / 5.0 + 32.0:.0f}°F"
        else:
            fl_p_str = f"FL {self.fl_bar:.2f}b"
            rl_p_str = f"RL {self.rl_bar:.2f}b"
            fr_p_str = f"{self.fr_bar:.2f}b FR"
            rr_p_str = f"{self.rr_bar:.2f}b RR"
            fl_t_str = f"{self.fl_temp:.0f}°C"
            rl_t_str = f"{self.rl_temp:.0f}°C"
            fr_t_str = f"{self.fr_temp:.0f}°C"
            rr_t_str = f"{self.rr_temp:.0f}°C"

        painter.setFont(QFont("Consolas", font_bar_sz, QFont.Weight.Bold))
        painter.setPen(self._color_for_bar(self.fl_bar))
        painter.drawText(QRectF(10, cy - wheel_dy - 12, left_col_w, 16), Qt.AlignmentFlag.AlignLeft, fl_p_str)
        painter.setFont(QFont("Segoe UI", font_temp_sz, QFont.Weight.Normal))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(10, cy - wheel_dy + 4, left_col_w, 14), Qt.AlignmentFlag.AlignLeft, fl_t_str)

        painter.setFont(QFont("Consolas", font_bar_sz, QFont.Weight.Bold))
        painter.setPen(self._color_for_bar(self.rl_bar))
        painter.drawText(QRectF(10, cy + wheel_dy - 10, left_col_w, 16), Qt.AlignmentFlag.AlignLeft, rl_p_str)
        painter.setFont(QFont("Segoe UI", font_temp_sz, QFont.Weight.Normal))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(10, cy + wheel_dy + 6, left_col_w, 14), Qt.AlignmentFlag.AlignLeft, rl_t_str)

        right_x = cx + wheel_dx + tw + 10.0
        right_col_w = max(40.0, w - right_x - 10.0)

        painter.setFont(QFont("Consolas", font_bar_sz, QFont.Weight.Bold))
        painter.setPen(self._color_for_bar(self.fr_bar))
        painter.drawText(QRectF(right_x, cy - wheel_dy - 12, right_col_w, 16), Qt.AlignmentFlag.AlignRight, fr_p_str)
        painter.setFont(QFont("Segoe UI", font_temp_sz, QFont.Weight.Normal))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(right_x, cy - wheel_dy + 4, right_col_w, 14), Qt.AlignmentFlag.AlignRight, fr_t_str)

        painter.setFont(QFont("Consolas", font_bar_sz, QFont.Weight.Bold))
        painter.setPen(self._color_for_bar(self.rr_bar))
        painter.drawText(QRectF(right_x, cy + wheel_dy - 10, right_col_w, 16), Qt.AlignmentFlag.AlignRight, rr_p_str)
        painter.setFont(QFont("Segoe UI", font_temp_sz, QFont.Weight.Normal))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(right_x, cy + wheel_dy + 6, right_col_w, 14), Qt.AlignmentFlag.AlignRight, rr_t_str)

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
        self.unit_system = "METRIC"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(85)

    def set_unit_system(self, unit_system: str) -> None:
        self.unit_system = unit_system
        self.update()

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

        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 8, 8)

        hdr_font_sz = max(7, min(11, int(w * 0.026)))
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(14, 8, w - 28, 18), Qt.AlignmentFlag.AlignLeft, "AWD TORQUE VECTORING")

        painter.setPen(COLOR_MINT_BRIGHT)
        painter.drawText(QRectF(14, 8, w - 28, 18), Qt.AlignmentFlag.AlignRight, f"● {self.bias_mode}")

        bar_left = max(60.0, w * 0.22)
        val_w = max(70.0, w * 0.28)
        bar_right = w - val_w - 8.0
        bar_w = max(40.0, bar_right - bar_left)
        bar_h = max(5.0, min(12.0, h * 0.10))

        lbl_font_sz = max(6, min(11, int(h * 0.11)))
        val_font_sz = max(7, min(12, int(h * 0.12)))

        content_h = h - 28.0
        y1 = 28.0 + (content_h * 0.32)
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", lbl_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(12, y1 - 4, bar_left - 16, 16), Qt.AlignmentFlag.AlignLeft, "F-AXLE")

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_left, y1, bar_w, bar_h), 2.5, 2.5)

        f_fill = bar_w * (self.front_pct / 100.0)
        painter.setBrush(QBrush(COLOR_MINT))
        painter.drawRoundedRect(QRectF(bar_left, y1, f_fill, bar_h), 2.5, 2.5)

        is_imp = (getattr(self, "unit_system", "METRIC") == "IMPERIAL")
        f_val_str = f"{int(self.front_pct)}% {int(self.front_nm * 0.73756)}lb-ft" if is_imp else f"{int(self.front_pct)}% {int(self.front_nm)}Nm"
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.setFont(QFont("Consolas", val_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(w - val_w - 8, y1 - 4, val_w, 16), Qt.AlignmentFlag.AlignRight, f_val_str)

        y2 = 28.0 + (content_h * 0.70)
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", lbl_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(12, y2 - 4, bar_left - 16, 16), Qt.AlignmentFlag.AlignLeft, "R-AXLE")

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_left, y2, bar_w, bar_h), 2.5, 2.5)

        r_fill = bar_w * (self.rear_pct / 100.0)
        r_color = COLOR_MINT_BRIGHT if self.rear_pct < 65.0 else COLOR_AMBER
        painter.setBrush(QBrush(r_color))
        painter.drawRoundedRect(QRectF(bar_left, y2, r_fill, bar_h), 2.5, 2.5)

        r_val_str = f"{int(self.rear_pct)}% {int(self.rear_nm * 0.73756)}lb-ft" if is_imp else f"{int(self.rear_pct)}% {int(self.rear_nm)}Nm"
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.setFont(QFont("Consolas", val_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(w - val_w - 8, y2 - 4, val_w, 16), Qt.AlignmentFlag.AlignRight, r_val_str)

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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(18)

    def set_power(self, power_kw: float) -> None:
        self.power_kw = power_kw
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_h = max(5.0, min(10.0, h * 0.45))
        y = (h - bar_h) / 2.0

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, y, w, bar_h), 3, 3)

        center_x = w * (self.max_regen_kw / (self.max_kw + self.max_regen_kw))
        painter.setPen(QPen(COLOR_TEXT_MUTED, 1.5))
        painter.drawLine(int(center_x), int(y - 2), int(center_x), int(y + bar_h + 2))

        if self.power_kw < -0.2:
            ratio = min(1.0, abs(self.power_kw) / self.max_regen_kw)
            fill_w = center_x * ratio
            fill_rect = QRectF(center_x - fill_w, y, fill_w, bar_h)
            painter.setBrush(QBrush(COLOR_MINT))
            painter.drawRoundedRect(fill_rect, 2, 2)
        elif self.power_kw > 0.2:
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
        self.unit_system = "METRIC"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(65)

        for _ in range(max_points):
            self.speed_history.append(0.0)
            self.power_history.append(0.0)

    def set_unit_system(self, unit_system: str) -> None:
        self.unit_system = unit_system
        self.update()

    def add_data_point(self, speed: float, power: float) -> None:
        self.speed_history.append(speed)
        self.power_history.append(power)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 8, 8)

        hdr_font_sz = max(6, min(10, int(w * 0.024)))
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(12, 6, w - 24, 14), Qt.AlignmentFlag.AlignLeft, "LIVE TELEMETRY WAVE")

        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(w - 70, 6, 30, 14), Qt.AlignmentFlag.AlignRight, "SPD")
        painter.setPen(COLOR_AMBER)
        painter.drawText(QRectF(w - 35, 6, 30, 14), Qt.AlignmentFlag.AlignRight, "PWR")

        grid_top = 22.0
        grid_h = h - grid_top - 6.0
        painter.setPen(QPen(QColor(0, 245, 160, 20), 1, Qt.PenStyle.DotLine))
        painter.drawLine(0, int(grid_top + grid_h * 0.33), w, int(grid_top + grid_h * 0.33))
        painter.drawLine(0, int(grid_top + grid_h * 0.66), w, int(grid_top + grid_h * 0.66))

        count = len(self.speed_history)
        if count < 2:
            painter.end()
            return

        step_x = (w - 8) / (self.max_points - 1)

        max_speed = 120.0 if getattr(self, "unit_system", "METRIC") == "IMPERIAL" else 180.0
        speed_path = QPainterPath()
        for i, val in enumerate(self.speed_history):
            clamped = max(0.0, min(max_speed, val))
            y = grid_top + grid_h - (clamped / max_speed) * grid_h
            x = 4 + (i * step_x)
            if i == 0:
                speed_path.moveTo(x, y)
            else:
                speed_path.lineTo(x, y)

        painter.setPen(QPen(COLOR_MINT, 1.8))
        painter.drawPath(speed_path)

        max_power = 120.0
        power_path = QPainterPath()
        for i, val in enumerate(self.power_history):
            clamped = max(-40.0, min(max_power, val))
            y = grid_top + grid_h - ((clamped + 40.0) / (max_power + 40.0)) * grid_h
            x = 4 + (i * step_x)
            if i == 0:
                power_path.moveTo(x, y)
            else:
                power_path.lineTo(x, y)

        painter.setPen(QPen(COLOR_AMBER, 1.2, Qt.PenStyle.DashLine))
        painter.drawPath(power_path)

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
        self.unit_system = "METRIC"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(35)

    def set_unit_system(self, unit_system: str) -> None:
        self.unit_system = unit_system
        self.update()

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
        h = self.height()
        items = [
            ("MOTOR", self.motor_temp, 75.0, 90.0),
            ("INVERTER", self.inverter_temp, 65.0, 80.0),
            ("BATTERY", self.batt_temp, 42.0, 50.0),
        ]

        col_w = w / len(items)
        lbl_font_sz = max(6, min(10, int(h * 0.20)))
        val_font_sz = max(8, min(13, int(h * 0.28)))

        for i, (label, temp, warn_th, crit_th) in enumerate(items):
            box_x = i * col_w + 3
            box_w = col_w - 6
            color = self._temp_color(temp, warn_th, crit_th)

            painter.setBrush(QBrush(COLOR_PANEL_BG))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
            painter.drawRoundedRect(QRectF(box_x, 0, box_w, h - 2), 5, 5)

            painter.setPen(COLOR_TEXT_MUTED)
            painter.setFont(QFont("Segoe UI", lbl_font_sz, QFont.Weight.Bold))
            painter.drawText(QRectF(box_x + 8, 3, box_w - 16, h * 0.35), Qt.AlignmentFlag.AlignLeft, label)

            is_imp = (getattr(self, "unit_system", "METRIC") == "IMPERIAL")
            disp_temp = (temp * 9.0 / 5.0 + 32.0) if is_imp else temp
            unit_sym = "°F" if is_imp else "°C"
            painter.setPen(color)
            painter.setFont(QFont("Consolas", val_font_sz, QFont.Weight.Bold))
            painter.drawText(
                QRectF(box_x + 8, h * 0.36, box_w - 24, h * 0.55),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{disp_temp:.1f}{unit_sym}",
            )

            pip_r = max(2.5, min(4.5, h * 0.08))
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(box_x + box_w - pip_r * 3.5, h * 0.65), pip_r, pip_r)

        painter.end()


class VoltesseDashboard(QMainWindow):
    """
    Main Automotive Digital Cockpit Cluster Window.
    Distraction-free, modern, sleek, high-contrast Cyber-Mint UI.
    Engineered with perfectly leveled symmetrical cards and proportional auto-scaling
    to deliver an authentic hypercar cockpit experience in fullscreen at any resolution.
    Supports Auto (PRNDB with D1-D6) and Sequential Manual transmissions across operating modes.
    """

    # Interactive signal events
    mode_switch_requested = pyqtSignal(str)   # "RACE", "SIMULATION", "TEST"
    simulation_input_changed = pyqtSignal(bool, bool, bool, bool) # (thr, brk, steer_l, steer_r)
    drive_mode_requested = pyqtSignal()
    transmission_toggle_requested = pyqtSignal() # Toggle Auto / Manual
    gear_up_requested = pyqtSignal()             # Shift Up (Manual or Auto)
    gear_down_requested = pyqtSignal()           # Shift Down (Manual or Auto)
    gear_shift_requested = pyqtSignal()          # Cycle gear (G key)
    logging_toggle_requested = pyqtSignal()      # Toggle DB logging (L key)
    units_toggle_requested = pyqtSignal()        # Toggle Metric / Imperial (U key)
    units_changed = pyqtSignal(str)              # "METRIC" or "IMPERIAL"
    pause_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voltesse Dash - Digital Cockpit")
        self.setMinimumSize(800, 480)
        self.resize(1280, 720)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Active operating mode state
        self.current_mode = "RACE"
        self.current_transmission = "AUTO"
        self.unit_system = "METRIC"
        self._last_record: Optional[TelemetryRecord] = None

        # Track currently held keys for video game simulation
        self._held_keys: Set[int] = set()

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
        central_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(14, 8, 14, 10)
        self.main_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. TOP AUTOMOTIVE HUD RIBBON
        # -------------------------------------------------------------
        self.top_bar = QFrame()
        self.top_bar.setStyleSheet("background-color: rgba(6, 14, 10, 0.7); border-radius: 6px;")
        self.top_layout = QHBoxLayout(self.top_bar)
        self.top_layout.setContentsMargins(10, 0, 10, 0)
        self.top_layout.setSpacing(8)

        # Turn Signal Left
        self.left_blinker = QLabel("◄")
        self.left_blinker.setStyleSheet("color: #123226;")

        # Brand / Subtitle
        self.brand_label = QLabel("⚡ VOLTESSE")
        self.brand_label.setStyleSheet("color: #00F5A0; letter-spacing: 2px;")

        # Ready Indicator
        self.ready_badge = QLabel("READY")
        self.ready_badge.setStyleSheet(
            "color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4);"
        )

        # Database Logging Status Badge (REC / LOG OFF / R/O)
        self.logging_badge = QLabel("REC")
        self.logging_badge.setStyleSheet(
            "color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
        )

        # Unit System Status Badge (METRIC / IMPERIAL)
        self.units_badge = QLabel("METRIC")
        self.units_badge.setStyleSheet(
            "color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
        )

        # Operating Mode Ribbon Badge
        self.op_mode_badge = QLabel("RACE [CAN]")

        # Transmission & Active Gear Badge
        self.trans_mode_badge = QLabel("AUTO [D1]")
        self.trans_mode_badge.setStyleSheet(
            "background-color: rgba(0, 245, 160, 0.15); color: #5CFFC7; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4);"
        )

        # Drive Mode Pill (ECO / DRIVE / SPORT)
        self.mode_badge = QLabel("DRIVE")
        self.mode_badge.setStyleSheet(
            "background-color: rgba(0, 245, 160, 0.15); color: #5CFFC7; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4);"
        )

        # Controls Hint Pill
        self.controls_hint = QLabel("[KEYS: 1:RACE | 2:SIM | 3:TEST | T:TRANS | E/C:SHIFT]")
        self.controls_hint.setStyleSheet(
            "color: #4E7566; background-color: rgba(12, 26, 20, 0.6); padding: 2px 8px; border-radius: 4px;"
        )

        self._update_op_mode_badge_style("RACE")

        # Status / Warning Pill
        self.status_badge = QLabel("SYSTEM READY")
        self.status_badge.setStyleSheet(
            "background-color: rgba(0, 245, 160, 0.12); color: #5CFFC7; padding: 2px 8px; border-radius: 4px;"
        )

        # Ambient Temp
        self.ambient_label = QLabel("22°C")
        self.ambient_label.setStyleSheet("color: #9AE6B4;")

        # Live Clock
        self.clock_label = QLabel("12:00:00 AM")
        self.clock_label.setStyleSheet("color: #FFFFFF;")

        # Turn Signal Right
        self.right_blinker = QLabel("►")
        self.right_blinker.setStyleSheet("color: #123226;")

        self.top_layout.addWidget(self.left_blinker)
        self.top_layout.addSpacing(6)
        self.top_layout.addWidget(self.brand_label)
        self.top_layout.addSpacing(8)
        self.top_layout.addWidget(self.ready_badge)
        self.top_layout.addSpacing(6)
        self.top_layout.addWidget(self.logging_badge)
        self.top_layout.addSpacing(6)
        self.top_layout.addWidget(self.units_badge)
        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.op_mode_badge)
        self.top_layout.addSpacing(6)
        self.top_layout.addWidget(self.trans_mode_badge)
        self.top_layout.addSpacing(6)
        self.top_layout.addWidget(self.mode_badge)
        self.top_layout.addSpacing(6)
        self.top_layout.addWidget(self.controls_hint)
        self.top_layout.addSpacing(6)
        self.top_layout.addWidget(self.status_badge)
        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.ambient_label)
        self.top_layout.addSpacing(10)
        self.top_layout.addWidget(self.clock_label)
        self.top_layout.addSpacing(6)
        self.top_layout.addWidget(self.right_blinker)

        self.main_layout.addWidget(self.top_bar)

        # -------------------------------------------------------------
        # 2. MAIN COCKPIT PANORAMIC STAGE (Balanced Symmetrical Wings)
        # -------------------------------------------------------------
        self.stage_layout = QHBoxLayout()
        self.stage_layout.setContentsMargins(0, 0, 0, 0)
        self.stage_layout.setSpacing(14)

        # =============================================================
        # --- LEFT WING: Energy Station (2 Harmonious Cards) ---
        # =============================================================
        self.left_wing = QFrame()
        self.left_wing.setStyleSheet("background: transparent;")
        self.left_wing_layout = QVBoxLayout(self.left_wing)
        self.left_wing_layout.setContentsMargins(0, 0, 0, 0)
        self.left_wing_layout.setSpacing(10)

        # Card 1: Energy & Battery Hero Card (with integrated Voltage/Current)
        self.battery_widget = BatteryStatusWidget()
        self.left_wing_layout.addWidget(self.battery_widget, stretch=5)

        # Card 2: 4-Wheel TPMS Monitoring Card
        self.tpms_widget = TPMSWidget()
        self.left_wing_layout.addWidget(self.tpms_widget, stretch=5)

        # Backwards compatible mock references for tests
        self.left_hdr = QLabel("⚡ ENERGY & BATTERY")
        self.left_hdr.setVisible(False)
        self.volt_curr_pod = QFrame()
        self.volt_curr_pod.setVisible(False)
        self.energy_pod = QFrame()
        self.energy_pod.setVisible(False)
        self.v_lbl = QLabel()
        self.volt_val = QLabel("400.0 V")
        self.c_lbl = QLabel()
        self.amp_val = QLabel("+0.0 A")
        self.ep_hdr = QLabel()
        self.eff_val = QLabel("15.2 kWh/100km")
        self.hlth_hdr = QLabel()
        self.health_val = QLabel("100% NOMINAL")

        self.stage_layout.addWidget(self.left_wing, stretch=3)

        # =============================================================
        # --- CENTER STAGE: Hero Speedometer Dial ---
        # =============================================================
        self.center_stage = QFrame()
        self.center_stage.setStyleSheet("background: transparent;")
        self.center_layout = QVBoxLayout(self.center_stage)
        self.center_layout.setContentsMargins(0, 0, 0, 0)

        self.speed_gauge = SpeedometerDialWidget(min_val=0.0, max_val=180.0, title="SPEED", unit="KM/H")
        self.center_layout.addWidget(self.speed_gauge)

        self.stage_layout.addWidget(self.center_stage, stretch=4)

        # =============================================================
        # --- RIGHT WING: Dynamics Station (3 Harmonious Cards) ---
        # =============================================================
        self.right_wing = QFrame()
        self.right_wing.setStyleSheet("background: transparent;")
        self.right_wing_layout = QVBoxLayout(self.right_wing)
        self.right_wing_layout.setContentsMargins(0, 0, 0, 0)
        self.right_wing_layout.setSpacing(10)

        # Card 1: Net Power & Pedal Dynamics Pod
        self.power_pod = QFrame()
        self.power_pod.setStyleSheet(
            "background-color: rgba(8, 18, 14, 0.9); border: 1px solid rgba(18, 50, 38, 0.8); border-radius: 8px;"
        )
        pp_layout = QVBoxLayout(self.power_pod)
        pp_layout.setContentsMargins(14, 8, 14, 8)
        pp_layout.setSpacing(6)

        p_hdr_row = QHBoxLayout()
        self.right_hdr = QLabel("⚡ POWERTRAIN DYNAMICS")
        self.right_hdr.setStyleSheet("color: #9AE6B4; letter-spacing: 1px; font-weight: bold;")
        self.power_title = QLabel("NET POWER")
        self.power_title.setStyleSheet("color: #4E7566; font-weight: bold;")
        p_hdr_row.addWidget(self.right_hdr)
        p_hdr_row.addStretch(1)
        p_hdr_row.addWidget(self.power_title)
        pp_layout.addLayout(p_hdr_row)

        p_val_row = QHBoxLayout()
        self.power_val = QLabel("0.0 kW")
        self.power_val.setStyleSheet("color: #00F5A0; font-weight: bold;")
        p_val_row.addStretch(1)
        p_val_row.addWidget(self.power_val)
        pp_layout.addLayout(p_val_row)

        self.power_bar = PowerBarWidget()
        pp_layout.addWidget(self.power_bar)

        self.pedal_frame = QFrame()
        pedal_layout = QHBoxLayout(self.pedal_frame)
        pedal_layout.setContentsMargins(0, 2, 0, 0)

        self.throttle_label = QLabel("THR: 0%")
        self.throttle_label.setStyleSheet("color: #00F5A0; font-weight: bold;")
        self.brake_label = QLabel("BRK: 0%")
        self.brake_label.setStyleSheet("color: #FF4D6D; font-weight: bold;")

        pedal_layout.addWidget(self.throttle_label)
        pedal_layout.addStretch(1)
        pedal_layout.addWidget(self.brake_label)
        pp_layout.addWidget(self.pedal_frame)

        self.right_wing_layout.addWidget(self.power_pod, stretch=4)

        # Card 2: AWD Torque Vectoring Card
        self.awd_widget = AwdTorqueVectorWidget()
        self.right_wing_layout.addWidget(self.awd_widget, stretch=3)

        # Card 3: Live Oscilloscope Waveform Card
        self.sparkline_widget = LiveSparklineWidget(max_points=50)
        self.right_wing_layout.addWidget(self.sparkline_widget, stretch=3)

        self.stage_layout.addWidget(self.right_wing, stretch=3)

        self.main_layout.addLayout(self.stage_layout, stretch=4)

        # -------------------------------------------------------------
        # 3. BOTTOM TELEMETRY & TRIP DECK
        # -------------------------------------------------------------
        self.bottom_bar = QFrame()
        self.bottom_bar.setStyleSheet("background: transparent;")
        self.bottom_layout = QHBoxLayout(self.bottom_bar)
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_layout.setSpacing(12)

        # Unified Single-Pod Trip Odometer
        self.trip_pod = QFrame()
        self.trip_pod.setStyleSheet(
            "background-color: rgba(8, 18, 14, 0.9); border: 1px solid rgba(18, 50, 38, 0.8); border-radius: 8px;"
        )
        self.trip_layout = QVBoxLayout(self.trip_pod)
        self.trip_layout.setContentsMargins(10, 4, 10, 4)
        self.trip_layout.setSpacing(1)

        self.trip_hdr = QLabel("TRIP ODOMETER")
        self.trip_hdr.setStyleSheet("color: #4E7566; border: none; background: transparent;")

        self.trip_dist_val = QLabel("0.00 km")
        self.trip_dist_val.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")

        self.trip_layout.addWidget(self.trip_hdr)
        self.trip_layout.addWidget(self.trip_dist_val)
        self.bottom_layout.addWidget(self.trip_pod)

        # Thermal Diagnostics Pods
        self.thermal_widget = ThermalMonitorWidget()
        self.bottom_layout.addWidget(self.thermal_widget, stretch=1)

        self.main_layout.addWidget(self.bottom_bar)

        self._apply_dynamic_scale()

    def mousePressEvent(self, event) -> None:
        """Ensures cockpit window maintains primary keyboard focus upon clicks."""
        self.setFocus()
        super().mousePressEvent(event)

    def _apply_dynamic_scale(self) -> None:
        """Dynamically adjusts font sizes and spacings for crisp proportions across resolutions."""
        w = max(600, self.width())
        h = max(400, self.height())
        scale = max(0.80, min(2.0, min(w / 1280.0, h / 720.0)))

        top_h = max(36, min(56, int(42 * scale)))
        self.top_bar.setFixedHeight(top_h)

        bot_h = max(42, min(64, int(48 * scale)))
        self.bottom_bar.setFixedHeight(bot_h)

        self.trip_pod.setFixedWidth(max(120, min(220, int(150 * scale))))

        f_brand = QFont("Segoe UI", max(10, min(18, int(13 * scale))), QFont.Weight.Black)
        self.brand_label.setFont(f_brand)

        f_hud = QFont("Segoe UI", max(8, min(13, int(9 * scale))), QFont.Weight.Bold)
        self.ready_badge.setFont(f_hud)
        self.op_mode_badge.setFont(f_hud)
        self.trans_mode_badge.setFont(f_hud)
        self.mode_badge.setFont(f_hud)
        self.status_badge.setFont(f_hud)

        f_hint = QFont("Consolas", max(7, min(11, int(8 * scale))), QFont.Weight.Normal)
        self.controls_hint.setFont(f_hint)

        f_clock = QFont("Consolas", max(9, min(15, int(12 * scale))), QFont.Weight.Bold)
        self.clock_label.setFont(f_clock)
        self.ambient_label.setFont(f_clock)

        f_blinker = QFont("Segoe UI", max(10, min(16, int(12 * scale))), QFont.Weight.Bold)
        self.left_blinker.setFont(f_blinker)
        self.right_blinker.setFont(f_blinker)

        f_hdrs = QFont("Segoe UI", max(8, min(13, int(9 * scale))), QFont.Weight.Bold)
        self.right_hdr.setFont(f_hdrs)
        self.power_title.setFont(f_hdrs)

        f_lbl = QFont("Segoe UI", max(6, min(10, int(7 * scale))), QFont.Weight.Bold)
        self.trip_hdr.setFont(f_lbl)

        f_val = QFont("Consolas", max(8, min(14, int(10 * scale))), QFont.Weight.Bold)
        self.throttle_label.setFont(f_val)
        self.brake_label.setFont(f_val)
        self.trip_dist_val.setFont(QFont("Consolas", max(9, min(16, int(12 * scale))), QFont.Weight.Bold))

        f_pwr = QFont("Consolas", max(11, min(22, int(16 * scale))), QFont.Weight.Bold)
        self.power_val.setFont(f_pwr)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_dynamic_scale()

    def _update_clock(self) -> None:
        self.clock_label.setText(time.strftime("%I:%M:%S %p"))

    def set_operating_mode(self, mode: str) -> None:
        """Updates the active operating mode display in the UI and resets held input keys."""
        self.current_mode = mode
        self._held_keys.clear()
        self._update_simulation_keys()
        self._update_op_mode_badge_style(mode)

    def _update_op_mode_badge_style(self, mode: str) -> None:
        if mode == "RACE":
            self.op_mode_badge.setText("RACE [CAN]")
            self.op_mode_badge.setStyleSheet(
                "background-color: rgba(0, 245, 160, 0.22); color: #00F5A0; padding: 2px 10px; border-radius: 4px; border: 1px solid #00F5A0; font-weight: bold;"
            )
            self.controls_hint.setText("[KEYS: 1:RACE | 2:SIM | 3:TEST | T:TRANS | E/C:SHIFT | U:UNITS | L:LOG]")
        elif mode == "SIMULATION":
            self.op_mode_badge.setText("SIMULATION [GAME]")
            self.op_mode_badge.setStyleSheet(
                "background-color: rgba(0, 229, 255, 0.22); color: #00E5FF; padding: 2px 10px; border-radius: 4px; border: 1px solid #00E5FF; font-weight: bold;"
            )
            self.controls_hint.setText("[T:TRANS | W/S:PEDALS | A/D:STEER | E/C:SHIFT | U:UNITS | L:LOG | M:MODE]")
        elif mode == "TEST":
            self.op_mode_badge.setText("TEST [MOCK]")
            self.op_mode_badge.setStyleSheet(
                "background-color: rgba(154, 230, 180, 0.20); color: #5CFFC7; padding: 2px 10px; border-radius: 4px; border: 1px solid #5CFFC7; font-weight: bold;"
            )
            self.controls_hint.setText("[TEST: AUTO ONLY | 1:RACE | 2:SIM | U:UNITS | L:LOG | SPACE:PAUSE]")

    def toggle_units(self) -> str:
        """Toggles between METRIC and IMPERIAL units across all dashboard widgets."""
        new_mode = "IMPERIAL" if self.unit_system == "METRIC" else "METRIC"
        self.set_unit_system(new_mode)
        return new_mode

    def set_unit_system(self, system: str) -> None:
        """Sets dashboard unit system to METRIC or IMPERIAL across all gauges and widgets."""
        self.unit_system = "IMPERIAL" if system.upper() == "IMPERIAL" else "METRIC"
        is_imp = (self.unit_system == "IMPERIAL")

        if is_imp:
            self.units_badge.setText("IMPERIAL")
            self.units_badge.setStyleSheet(
                "color: #00E5FF; background-color: rgba(0, 229, 255, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 229, 255, 0.4); font-weight: bold;"
            )
            self.ambient_label.setText("72°F")
            self.speed_gauge.set_units(unit="MPH", max_val=120.0)
        else:
            self.units_badge.setText("METRIC")
            self.units_badge.setStyleSheet(
                "color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
            )
            self.ambient_label.setText("22°C")
            self.speed_gauge.set_units(unit="KM/H", max_val=180.0)

        self.battery_widget.set_unit_system(self.unit_system)
        self.tpms_widget.set_unit_system(self.unit_system)
        self.thermal_widget.set_unit_system(self.unit_system)
        self.awd_widget.set_unit_system(self.unit_system)
        self.sparkline_widget.set_unit_system(self.unit_system)

        if hasattr(self, "_last_record") and self._last_record is not None:
            self.update_telemetry(self._last_record)

        self.units_changed.emit(self.unit_system)
        self.units_toggle_requested.emit()

    def set_logging_state(self, write_enabled: bool, read_only: bool = False) -> None:
        """Updates top ribbon database logging badge."""
        if read_only:
            self.logging_badge.setText("R/O")
            self.logging_badge.setStyleSheet(
                "color: #00E5FF; background-color: rgba(0, 229, 255, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 229, 255, 0.4); font-weight: bold;"
            )
        elif write_enabled:
            self.logging_badge.setText("REC")
            self.logging_badge.setStyleSheet(
                "color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
            )
        else:
            self.logging_badge.setText("LOG OFF")
            self.logging_badge.setStyleSheet(
                "color: #FFB800; background-color: rgba(255, 184, 0, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(255, 184, 0, 0.4); font-weight: bold;"
            )

    def update_telemetry(self, record: TelemetryRecord) -> None:
        """
        Non-blocking slot updating all telemetry gauges and HUD indicators.
        """
        self._last_record = record
        gear = record.gear if hasattr(record, "gear") and record.gear else "D1"
        trans_mode = record.transmission_mode if hasattr(record, "transmission_mode") and record.transmission_mode else "AUTO"
        self.current_transmission = trans_mode

        is_imp = (self.unit_system == "IMPERIAL")
        disp_speed = (record.speed_kmh * 0.621371) if is_imp else record.speed_kmh

        # Central Speedometer Dial
        self.speed_gauge.set_value(disp_speed, sub_val=str(record.motor_rpm))
        self.speed_gauge.set_pedals_and_gear(
            throttle=record.throttle_pct,
            brake=record.brake_pct,
            gear=gear,
            mode=record.drive_mode,
            steering_angle=record.steering_angle,
            transmission_mode=trans_mode,
        )

        # Transmission Badge in Top Ribbon
        display_gear = f"M{gear}" if (trans_mode == "MANUAL" and gear.isdigit()) else gear
        if trans_mode == "MANUAL":
            self.trans_mode_badge.setText(f"MANUAL [{display_gear}]")
            self.trans_mode_badge.setStyleSheet(
                "background-color: rgba(0, 229, 255, 0.25); color: #00E5FF; padding: 2px 8px; border-radius: 4px; border: 1px solid #00E5FF; font-weight: bold;"
            )
        else:
            self.trans_mode_badge.setText(f"AUTO [{display_gear}]")
            self.trans_mode_badge.setStyleSheet(
                "background-color: rgba(0, 245, 160, 0.15); color: #5CFFC7; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
            )

        # Battery & Voltage
        self.battery_widget.set_battery_data(
            record.battery_soc, record.battery_voltage, record.battery_current
        )
        self.volt_val.setText(f"{record.battery_voltage:.1f} V")
        self.amp_val.setText(f"{record.battery_current:+.1f} A")

        # Power & Regen
        self.power_val.setText(f"{record.battery_power_kw:+.1f} kW")
        if record.battery_power_kw < -0.5:
            self.power_val.setStyleSheet("color: #00F5A0; font-weight: bold;")
        elif record.battery_power_kw > 60.0:
            self.power_val.setStyleSheet("color: #FFB800; font-weight: bold;")
        else:
            self.power_val.setStyleSheet("color: #5CFFC7; font-weight: bold;")

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
        disp_dist = (record.trip_distance_km * 0.621371) if is_imp else record.trip_distance_km
        dist_unit = "mi" if is_imp else "km"
        self.trip_dist_val.setText(f"{disp_dist:.2f} {dist_unit}")

        # Sparkline trace
        self.sparkline_widget.add_data_point(disp_speed, record.battery_power_kw)

        # Dynamic AWD Dual-Motor Torque Calculation
        if record.battery_power_kw < -0.5:
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

        # Dynamic TPMS
        temp_base = 28.0 + min(12.0, (record.speed_kmh / 180.0) * 7.0 + (record.trip_distance_km * 0.08))
        fl_t = temp_base + 1.2
        fr_t = temp_base + 0.8
        rl_t = temp_base - 0.4
        rr_t = temp_base - 0.6

        fl_p = 2.40 + (fl_t - 25.0) * 0.004
        fr_p = 2.40 + (fr_t - 25.0) * 0.004
        rl_p = 2.38 + (rl_t - 25.0) * 0.004
        rr_p = 2.38 + (rr_t - 25.0) * 0.004
        self.tpms_widget.set_tpms(fl_p, fr_p, rl_p, rr_p, fl_t, fr_t, rl_t, rr_t)

    def _update_simulation_keys(self) -> None:
        """Dispatches active driving controls to simulation stream."""
        thr = (Qt.Key.Key_W in self._held_keys or Qt.Key.Key_Up in self._held_keys)
        brk = (Qt.Key.Key_S in self._held_keys or Qt.Key.Key_Down in self._held_keys)
        steer_l = (Qt.Key.Key_A in self._held_keys or Qt.Key.Key_Left in self._held_keys)
        steer_r = (Qt.Key.Key_D in self._held_keys or Qt.Key.Key_Right in self._held_keys)
        self.simulation_input_changed.emit(thr, brk, steer_l, steer_r)

    def keyPressEvent(self, event) -> None:
        """Handles mode switching, auto/manual transmission, and video-game controls."""
        key = event.key()

        # Prevent OS auto-repeat for one-shot action hotkeys
        if event.isAutoRepeat():
            if key not in (
                Qt.Key.Key_W, Qt.Key.Key_Up,
                Qt.Key.Key_S, Qt.Key.Key_Down,
                Qt.Key.Key_A, Qt.Key.Key_Left,
                Qt.Key.Key_D, Qt.Key.Key_Right,
            ):
                return

        # Quit
        if key in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()
            return

        # Fullscreen Toggle
        elif key == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
            return

        # Mode Selection Hotkeys (Standard number row, F-keys, and numpad keys)
        elif key in (Qt.Key.Key_1, Qt.Key.Key_F1):
            self.mode_switch_requested.emit("RACE")
            return
        elif key in (Qt.Key.Key_2, Qt.Key.Key_F2):
            self.mode_switch_requested.emit("SIMULATION")
            return
        elif key in (Qt.Key.Key_3, Qt.Key.Key_F3):
            self.mode_switch_requested.emit("TEST")
            return
        elif key == Qt.Key.Key_Tab:
            order = ["RACE", "SIMULATION", "TEST"]
            curr_idx = order.index(self.current_mode) if self.current_mode in order else 0
            next_mode = order[(curr_idx + 1) % len(order)]
            self.mode_switch_requested.emit(next_mode)
            return

        # Transmission Toggle (Auto <-> Manual) - Disabled in Test Mode
        elif key == Qt.Key.Key_T:
            if self.current_mode == "TEST":
                self.status_badge.setText("⚠️ TEST MODE: AUTO ONLY")
                self.status_badge.setStyleSheet(
                    "background-color: rgba(255, 184, 0, 0.25); color: #FFB800; padding: 2px 8px; border-radius: 4px; font-weight: bold;"
                )
            else:
                self.transmission_toggle_requested.emit()
            return

        # Manual / Sequential Gear Shifting (E: Shift Up, C: Shift Down)
        elif key == Qt.Key.Key_E:
            self.gear_up_requested.emit()
            return
        elif key == Qt.Key.Key_C:
            self.gear_down_requested.emit()
            return

        # Vehicle Controls
        elif key == Qt.Key.Key_M:
            self.drive_mode_requested.emit()
            return
        elif key == Qt.Key.Key_G:
            self.gear_shift_requested.emit()
            return
        elif key == Qt.Key.Key_L:
            self.logging_toggle_requested.emit()
            return
        elif key == Qt.Key.Key_U:
            self.toggle_units()
            return
        elif key == Qt.Key.Key_Space:
            self.pause_requested.emit()
            return

        # Video Game Driving Inputs (W/A/S/D and Arrow Keys)
        if key in (
            Qt.Key.Key_W, Qt.Key.Key_Up,
            Qt.Key.Key_S, Qt.Key.Key_Down,
            Qt.Key.Key_A, Qt.Key.Key_Left,
            Qt.Key.Key_D, Qt.Key.Key_Right,
        ):
            self._held_keys.add(key)
            self._update_simulation_keys()
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        """Handles key release without auto-repeat interruptions."""
        if event.isAutoRepeat():
            return

        key = event.key()
        if key in self._held_keys:
            self._held_keys.remove(key)
            self._update_simulation_keys()
            return

        super().keyReleaseEvent(event)
