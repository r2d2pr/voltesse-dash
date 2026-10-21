"""
Voltesse Dash - Modern Automotive Digital Cockpit GUI
A sleek, distraction-free instrument cluster engineered for embedded
in-vehicle displays (e.g. Raspberry Pi automotive HUD / cluster screens).
Features a high-contrast Cyber-Mint aesthetic with full auto-scaling to variable
fullscreen resolutions and interactive video-game simulation controls.
Supports Automatic (PRNDB with dynamic speed-based D1-D6 gear display)
and 6-Speed Sequential Manual (R, N, 1-6) transmissions.
"""

from __future__ import annotations

from collections import deque
import math
import time
from typing import Deque, List, Optional, Set, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
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
        max_val: float = 120.0,
        title: str = "SPEED",
        unit: str = "MPH",
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

        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 160)
        self.setMinimumWidth(0)

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

        padding = max(14.0, side * 0.065)
        outer_r = (side / 2.0) - padding
        track_r = outer_r - (side * 0.025)
        track_w = max(4.0, min(12.0, side * 0.026))

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
                r_num = r_inner - (side * 0.038)
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
        font_speed_size = max(18, min(60, int(side * 0.125)))
        font_speed = QFont("Segoe UI", font_speed_size, QFont.Weight.Bold)
        painter.setFont(font_speed)
        painter.setPen(COLOR_TEXT_PRIMARY)

        speed_box_w = side * 0.70
        speed_box_h = side * 0.22
        speed_rect = QRectF(cx - (speed_box_w / 2.0), cy - side * 0.27, speed_box_w, speed_box_h)
        painter.drawText(speed_rect, Qt.AlignmentFlag.AlignCenter, f"{speed_int}")

        # 8. Speed Unit Label
        painter.setPen(COLOR_MINT)
        font_unit = QFont("Segoe UI", max(7, min(14, int(side * 0.026))), QFont.Weight.Bold)
        font_unit.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(1, int(side * 0.005)))
        painter.setFont(font_unit)
        unit_h = max(11.0, side * 0.045)
        unit_rect = QRectF(cx - side * 0.20, cy - side * 0.045, side * 0.40, unit_h)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, self.unit)

        # 9. Modern Automotive Transmission Hub (Auto PRNDB with active gear or Manual R/N/1-6)
        gear_y = cy + side * 0.012
        if self.transmission_mode == "MANUAL":
            gears = ["R", "N", "1", "2", "3", "4", "5", "6"]
        else:
            gears = ["P", "R", "N", "D", "B"]

        slot_w = max(13.0, min(28.0, (side * 0.40) / len(gears)))
        box_h = max(13.0, min(20.0, side * 0.042))
        total_gear_w = len(gears) * slot_w
        start_gx = cx - (total_gear_w / 2.0)

        capsule_rect = QRectF(start_gx - 4, gear_y - 2, total_gear_w + 8, box_h + 4)
        painter.setBrush(QBrush(QColor(6, 14, 10, 200)))
        painter.setPen(QPen(QColor(18, 50, 38, 160), 1))
        painter.drawRoundedRect(capsule_rect, 5, 5)

        font_gear = QFont("Segoe UI", max(6, min(10, int(side * 0.020))), QFont.Weight.Bold)
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
        trans_status_y = gear_y + box_h + max(2.0, side * 0.008)
        status_h = max(11.0, min(15.0, side * 0.034))
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
        font_status = QFont("Segoe UI", max(6, min(10, int(side * 0.019))), QFont.Weight.Bold)
        font_status.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        painter.setFont(font_status)
        status_rect = QRectF(cx - side * 0.44, trans_status_y, side * 0.88, status_h)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, status_text)

        # RPM Subtitle
        rpm_y = trans_status_y + status_h + max(1.0, side * 0.006)
        rpm_h = max(9.0, min(12.0, side * 0.024))
        painter.setPen(COLOR_TEXT_SECONDARY)
        font_rpm = QFont("Consolas", max(6, min(10, int(side * 0.018))), QFont.Weight.Normal)
        painter.setFont(font_rpm)
        rpm_rect = QRectF(cx - side * 0.35, rpm_y, side * 0.70, rpm_h)
        painter.drawText(rpm_rect, Qt.AlignmentFlag.AlignCenter, f"{self.sub_val_label} {self.sub_val}")

        # 10. Dual Horizontal Micro-Meters for Throttle & Brake (Centered collision-free)
        pedal_y = rpm_y + rpm_h + max(2.0, side * 0.008)
        bar_w = max(20.0, min(34.0, side * 0.085))
        bar_h = max(3.0, min(5.0, side * 0.012))
        lbl_w = max(18.0, min(24.0, side * 0.060))
        gap = max(3.0, side * 0.010)

        # Center labels between the two bars
        font_pedal_lbl = QFont("Segoe UI", max(5, min(8, int(side * 0.018))), QFont.Weight.Bold)
        painter.setFont(font_pedal_lbl)
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(cx - gap - lbl_w, pedal_y - 3, lbl_w, bar_h + 6), Qt.AlignmentFlag.AlignCenter, "BRK")
        painter.drawText(QRectF(cx + gap, pedal_y - 3, lbl_w, bar_h + 6), Qt.AlignmentFlag.AlignCenter, "THR")

        # Brake Micro-Meter (Left of BRK label)
        brk_bx = cx - gap - lbl_w - bar_w
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(brk_bx, pedal_y, bar_w, bar_h), 2, 2)
        brk_fill = bar_w * (min(100.0, self.brake_pct) / 100.0)
        if brk_fill > 0:
            painter.setBrush(QBrush(COLOR_RED))
            painter.drawRoundedRect(QRectF(brk_bx + bar_w - brk_fill, pedal_y, brk_fill, bar_h), 2, 2)

        # Throttle Micro-Meter (Right of THR label)
        thr_bx = cx + gap + lbl_w
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(thr_bx, pedal_y, bar_w, bar_h), 2, 2)
        thr_fill = bar_w * (min(100.0, self.throttle_pct) / 100.0)
        if thr_fill > 0:
            painter.setBrush(QBrush(COLOR_MINT))
            painter.drawRoundedRect(QRectF(thr_bx, pedal_y, thr_fill, bar_h), 2, 2)

        # 11. Center Steering Wheel Angle Indicator
        steer_y = pedal_y + bar_h + max(2.0, side * 0.008)
        angle = self.steering_angle
        steer_txt = f"STR ◄ {abs(int(angle))}°" if angle < -0.5 else (f"STR {int(angle)}° ►" if angle > 0.5 else "STR 0°")
        s_color = COLOR_CYAN if abs(angle) > 1.0 else COLOR_TEXT_MUTED

        painter.setPen(s_color)
        painter.setFont(QFont("Segoe UI", max(5, min(9, int(side * 0.018))), QFont.Weight.Bold))
        painter.drawText(QRectF(cx - 40, steer_y, 80, 12), Qt.AlignmentFlag.AlignCenter, steer_txt)

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
        self.unit_system = "IMPERIAL"
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)
        self.setMinimumWidth(0)

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

        # Responsive card header
        hdr_font_sz = max(7, min(11, int(w * 0.032)))
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        title_str = "⚡ BATTERY" if w < 260 else "⚡ ENERGY & BATTERY"
        status_str = "● NOMINAL" if w < 260 else "● PACK NOMINAL"

        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(QRectF(12, 7, w * 0.52, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_str)
        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(w * 0.48, 7, w * 0.52 - 12, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, status_str)

        if self.soc > 30.0:
            bar_color = COLOR_MINT
        elif self.soc > 15.0:
            bar_color = COLOR_AMBER
        else:
            bar_color = COLOR_RED

        card_content_h = h - 24.0
        arc_r = min(w * 0.17, card_content_h * 0.28)
        arc_cx = arc_r + max(10.0, w * 0.04)
        arc_cy = 22.0 + (card_content_h * 0.36)
        arc_rect = QRectF(arc_cx - arc_r, arc_cy - arc_r, arc_r * 2, arc_r * 2)

        start_ang = 210.0
        span_ang = -240.0
        pen_w = max(3.5, min(7.5, arc_r * 0.17))
        pen_track = QPen(COLOR_GAUGE_TRACK, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_track)
        painter.drawArc(arc_rect, int(start_ang * 16), int(span_ang * 16))

        active_span = span_ang * (self.soc / 100.0)
        if self.soc > 0.5:
            pen_active = QPen(bar_color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_active)
            painter.drawArc(arc_rect, int(start_ang * 16), int(active_span * 16))

        painter.setPen(COLOR_TEXT_PRIMARY)
        font_soc_sz = max(7, min(15, int(arc_r * 0.35)))
        painter.setFont(QFont("Segoe UI", font_soc_sz, QFont.Weight.Bold))
        painter.drawText(
            QRectF(arc_cx - arc_r + 2, arc_cy - arc_r * 0.5, (arc_r - 2) * 2, arc_r),
            Qt.AlignmentFlag.AlignCenter,
            f"{int(round(self.soc))}%",
        )

        range_x = arc_cx + arc_r + max(8.0, w * 0.04)
        range_w = max(50.0, w - range_x - 10.0)

        painter.setPen(COLOR_TEXT_MUTED)
        font_sub_sz = max(6, min(9, int(card_content_h * 0.05)))
        painter.setFont(QFont("Segoe UI", font_sub_sz, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(range_x, arc_cy - (card_content_h * 0.22), range_w, card_content_h * 0.18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "EST. RANGE",
        )

        painter.setPen(COLOR_MINT)
        font_range_sz = max(11, min(18, int(card_content_h * 0.095)))
        painter.setFont(QFont("Segoe UI", font_range_sz, QFont.Weight.Bold))
        if getattr(self, "unit_system", "METRIC") == "IMPERIAL":
            range_val = int(round(self.est_range_km * 0.621371))
            range_text = f"{range_val} mi"
        else:
            range_text = f"{int(round(self.est_range_km))} km"
        painter.drawText(
            QRectF(range_x, arc_cy - (card_content_h * 0.02), range_w, card_content_h * 0.24),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            range_text,
        )

        # Bottom Pod: Balanced dual-column electrical diagnostics
        sub_y = h - max(26.0, min(38.0, h * 0.18))
        sub_h = h - sub_y - 6.0
        sub_rect = QRectF(10, sub_y, w - 20, sub_h)
        painter.setBrush(QBrush(QColor(6, 14, 10, 190)))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
        painter.drawRoundedRect(sub_rect, 4, 4)

        font_pod_lbl = QFont("Segoe UI", max(6, min(8, int(sub_h * 0.30))), QFont.Weight.Bold)
        font_pod_val = QFont("Consolas", max(7, min(10, int(sub_h * 0.36))), QFont.Weight.Bold)

        col_w = (w - 28.0) / 2.0
        col1_x = 14.0
        col2_x = 14.0 + col_w

        # Subtle separator line between columns
        painter.setPen(QPen(COLOR_PANEL_BORDER, 0.6))
        painter.drawLine(int(col2_x), int(sub_y + 4), int(col2_x), int(sub_y + sub_h - 4))

        # VOLT
        painter.setFont(font_pod_lbl)
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(col1_x + 2, sub_y, 30, sub_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "VOLT")
        painter.setFont(font_pod_val)
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(QRectF(col1_x + 32, sub_y, col_w - 34, sub_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{self.voltage:.1f} V")

        # CURR
        painter.setFont(font_pod_lbl)
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(col2_x + 6, sub_y, 30, sub_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "CURR")
        painter.setFont(font_pod_val)
        c_color = COLOR_MINT if self.current < -0.5 else (COLOR_AMBER if self.current > 70.0 else COLOR_TEXT_PRIMARY)
        painter.setPen(c_color)
        painter.drawText(QRectF(col2_x + 36, sub_y, col_w - 38, sub_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{self.current:+.1f} A")

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
        self.unit_system = "IMPERIAL"
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)
        self.setMinimumWidth(0)

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

        # Header
        hdr_font_sz = max(7, min(11, int(w * 0.024)))
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(14, 8, w * 0.5, 18), Qt.AlignmentFlag.AlignLeft, "TIRE PRESSURE & TPMS")

        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(w * 0.5, 8, w * 0.5 - 14, 18), Qt.AlignmentFlag.AlignRight, "● ALL NOMINAL")

        content_h = h - 30.0
        cx = w / 2.0
        cy = 30.0 + (content_h / 2.0)

        is_imp = (getattr(self, "unit_system", "METRIC") == "IMPERIAL")

        if w > 400:
            # Full-Width Panoramic Page Layout
            ch = max(40.0, min(180.0, content_h * 0.62))
            cw = max(24.0, min(95.0, ch * 0.52))

            chassis_rect = QRectF(cx - cw / 2.0, cy - ch / 2.0, cw, ch)
            painter.setBrush(QBrush(QColor(10, 24, 18, 230)))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 1.4))
            painter.drawRoundedRect(chassis_rect, 10, 10)

            # Windshield & cockpit details
            painter.setPen(QPen(QColor(0, 245, 160, 90), 1.2))
            painter.drawLine(int(cx - cw * 0.36), int(cy - ch * 0.18), int(cx + cw * 0.36), int(cy - ch * 0.18))
            painter.drawLine(int(cx - cw * 0.32), int(cy + ch * 0.22), int(cx + cw * 0.32), int(cy + ch * 0.22))

            # Battery Pack Glow in Floor
            batt_floor = QRectF(cx - cw * 0.32, cy - ch * 0.12, cw * 0.64, ch * 0.32)
            painter.setBrush(QBrush(QColor(0, 245, 160, 25)))
            painter.setPen(QPen(QColor(0, 245, 160, 60), 0.8))
            painter.drawRoundedRect(batt_floor, 3, 3)

            # Wheels
            tw = max(4.0, min(14.0, cw * 0.18))
            th = max(8.0, min(28.0, ch * 0.22))
            wheel_dx = cw * 0.60
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
                painter.drawRoundedRect(QRectF(wx, wy, tw, th), 3, 3)

            if is_imp:
                tires_data = [
                    ("FRONT LEFT", f"{self.fl_bar * 14.5038:.1f} psi", f"{self.fl_temp * 9.0 / 5.0 + 32.0:.0f}°F", self.fl_bar, True, True),
                    ("FRONT RIGHT", f"{self.fr_bar * 14.5038:.1f} psi", f"{self.fr_temp * 9.0 / 5.0 + 32.0:.0f}°F", self.fr_bar, False, True),
                    ("REAR LEFT", f"{self.rl_bar * 14.5038:.1f} psi", f"{self.rl_temp * 9.0 / 5.0 + 32.0:.0f}°F", self.rl_bar, True, False),
                    ("REAR RIGHT", f"{self.rr_bar * 14.5038:.1f} psi", f"{self.rr_temp * 9.0 / 5.0 + 32.0:.0f}°F", self.rr_bar, False, False),
                ]
            else:
                tires_data = [
                    ("FRONT LEFT", f"{self.fl_bar:.2f} bar", f"{self.fl_temp:.0f}°C", self.fl_bar, True, True),
                    ("FRONT RIGHT", f"{self.fr_bar:.2f} bar", f"{self.fr_temp:.0f}°C", self.fr_bar, False, True),
                    ("REAR LEFT", f"{self.rl_bar:.2f} bar", f"{self.rl_temp:.0f}°C", self.rl_bar, True, False),
                    ("REAR RIGHT", f"{self.rr_bar:.2f} bar", f"{self.rr_temp:.0f}°C", self.rr_bar, False, False),
                ]

            card_w = max(110.0, min(170.0, w * 0.22))
            card_h = max(45.0, min(76.0, content_h * 0.32))

            for pos_lbl, press_str, temp_str, p_val, is_left, is_front in tires_data:
                c_x = 24.0 if is_left else (w - 24.0 - card_w)
                c_y = (cy - wheel_dy - card_h / 2.0) if is_front else (cy + wheel_dy - card_h / 2.0)

                c_rect = QRectF(c_x, c_y, card_w, card_h)
                painter.setBrush(QBrush(QColor(8, 18, 14, 210)))
                painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
                painter.drawRoundedRect(c_rect, 6, 6)

                painter.setFont(QFont("Segoe UI", max(6, min(8, int(card_h * 0.16))), QFont.Weight.Bold))
                painter.setPen(COLOR_TEXT_MUTED)
                painter.drawText(QRectF(c_x + 8, c_y + 4, card_w - 16, card_h * 0.25), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, pos_lbl)

                painter.setFont(QFont("Consolas", max(9, min(15, int(card_h * 0.34))), QFont.Weight.Bold))
                painter.setPen(self._color_for_bar(p_val))
                painter.drawText(QRectF(c_x + 8, c_y + card_h * 0.28, card_w - 16, card_h * 0.38), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, press_str)

                painter.setFont(QFont("Segoe UI", max(6, min(9, int(card_h * 0.20))), QFont.Weight.DemiBold))
                painter.setPen(COLOR_TEXT_SECONDARY)
                painter.drawText(QRectF(c_x + 8, c_y + card_h * 0.66, card_w - 16, card_h * 0.30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{temp_str} • NOMINAL")

                painter.setPen(QPen(QColor(18, 50, 38, 140), 1, Qt.PenStyle.DashLine))
                start_lx = (c_x + card_w) if is_left else c_x
                target_lx = (cx - wheel_dx - tw) if is_left else (cx + wheel_dx + tw)
                painter.drawLine(int(start_lx), int(c_y + card_h / 2.0), int(target_lx), int(c_y + card_h / 2.0))

        else:
            # Compact Side Card Layout
            ch = max(28.0, min(75.0, content_h * 0.46))
            cw = max(16.0, min(44.0, ch * 0.56))

            chassis_rect = QRectF(cx - cw / 2.0, cy - ch / 2.0, cw, ch)
            painter.setBrush(QBrush(QColor(12, 30, 22, 220)))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 1.2))
            painter.drawRoundedRect(chassis_rect, 5, 5)

            painter.setPen(QPen(QColor(0, 245, 160, 70), 1))
            painter.drawLine(int(cx - cw * 0.35), int(cy - ch * 0.16), int(cx + cw * 0.35), int(cy - ch * 0.16))

            tw = max(3.5, min(7.0, cw * 0.20))
            th = max(5.0, min(14.0, ch * 0.22))
            wheel_dx = cw * 0.58
            wheel_dy = ch * 0.26
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

            font_bar_sz = max(5, min(9, int(content_h * 0.075)))
            font_temp_sz = max(5, min(8, int(content_h * 0.060)))
            left_col_w = max(35.0, cx - wheel_dx - tw - 12.0)

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
        self.unit_system = "IMPERIAL"
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(45)
        self.setMinimumWidth(0)

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

        # Responsive card header
        hdr_font_sz = max(7, min(11, int(w * 0.032)))
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        title_str = "AWD TORQUE" if w < 260 else "AWD TORQUE VECTORING"
        bias_clean = self.bias_mode.replace("AWD ", "") if w < 260 else self.bias_mode

        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(QRectF(12, 7, w * 0.52, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_str)
        painter.setPen(COLOR_MINT_BRIGHT)
        painter.drawText(QRectF(w * 0.48, 7, w * 0.52 - 12, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"● {bias_clean}")

        lbl_w = max(44.0, min(56.0, w * 0.18))
        bar_left = 12.0 + lbl_w + 4.0
        val_w = max(82.0, min(110.0, w * 0.38))
        bar_right = w - val_w - 6.0
        bar_w = max(35.0, bar_right - bar_left)
        bar_h = max(5.0, min(9.0, h * 0.07))

        lbl_font_sz = max(7, min(10, int(h * 0.075)))
        val_font_sz = max(7, min(10, int(h * 0.075)))

        content_h = h - 28.0
        y1 = 28.0 + (content_h * 0.28)
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", lbl_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(12, y1 - 8, lbl_w, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "F-AXLE")

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
        painter.drawText(QRectF(w - val_w - 6, y1 - 8, val_w, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f_val_str)

        y2 = 28.0 + (content_h * 0.68)
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", lbl_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(12, y2 - 8, lbl_w, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "R-AXLE")

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
        painter.drawText(QRectF(w - val_w - 6, y2 - 8, val_w, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, r_val_str)

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
        self.setMinimumWidth(0)

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
        self.unit_system = "IMPERIAL"
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(45)
        self.setMinimumWidth(0)

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
        self.unit_system = "IMPERIAL"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(28)
        self.setMinimumWidth(0)

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


class CompactSpeedPod(QWidget):
    """
    Compact digital speedometer & transmission pod for side wing integration.
    Ensures vehicle speed, gear, RPM, pedals, and steering remain prominently visible
    when Battery or Powertrain hero views occupy the center stage.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.speed = 0.0
        self.max_speed = 120.0
        self.unit = "MPH"
        self.gear = "D1"
        self.trans_mode = "AUTO"
        self.motor_rpm = 0
        self.throttle_pct = 0.0
        self.brake_pct = 0.0
        self.steer_angle = 0.0
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)

    def set_unit_system(self, unit_system: str) -> None:
        self.unit = "MPH"
        self.max_speed = 120.0
        self.update()

    def set_speed_data(
        self,
        speed: float,
        unit: str,
        max_speed: float,
        gear: str,
        trans_mode: str,
        rpm: int,
        throttle: float,
        brake: float,
        steer: float,
    ) -> None:
        self.speed = speed
        self.unit = unit
        self.max_speed = max_speed
        self.gear = gear
        self.trans_mode = trans_mode
        self.motor_rpm = rpm
        self.throttle_pct = throttle
        self.brake_pct = brake
        self.steer_angle = steer
        self.update()

    def set_speed_and_status(
        self,
        speed: float,
        gear: str = "D1",
        rpm: int = 0,
        throttle: float = 0.0,
        brake: float = 0.0,
        steering_angle: float = 0.0,
        transmission_mode: str = "AUTO",
        unit: Optional[str] = None,
        max_speed: Optional[float] = None,
    ) -> None:
        self.speed = speed
        if unit is not None:
            self.unit = unit
        if max_speed is not None:
            self.max_speed = max_speed
        elif self.unit == "MPH":
            self.max_speed = 120.0
        else:
            self.max_speed = 180.0
        self.gear = gear
        self.trans_mode = transmission_mode
        self.motor_rpm = rpm
        self.throttle_pct = throttle
        self.brake_pct = brake
        self.steer_angle = steering_angle
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

        # Header
        hdr_font_sz = max(7, min(10, int(w * 0.032)))
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(QRectF(12, 7, w * 0.50, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "⚡ SPEED")

        badge_str = f"{self.trans_mode} [{self.gear}]"
        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(w * 0.45, 7, w * 0.55 - 12, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, badge_str)

        content_h = h - 26.0

        # Large Digital Speed Number + Unit
        spd_y = 26.0 + (content_h * 0.04)
        spd_h = content_h * 0.42

        font_spd_sz = max(18, min(34, int(content_h * 0.32)))
        painter.setFont(QFont("Segoe UI", font_spd_sz, QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_PRIMARY)
        spd_str = f"{int(round(self.speed))}"
        painter.drawText(QRectF(12, spd_y, w * 0.55, spd_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, spd_str)

        font_unit_sz = max(7, min(11, int(content_h * 0.10)))
        painter.setFont(QFont("Segoe UI", font_unit_sz, QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(w * 0.52, spd_y + (spd_h * 0.12), w * 0.44, spd_h * 0.40), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.unit)

        font_rpm_sz = max(6, min(9, int(content_h * 0.08)))
        painter.setFont(QFont("Consolas", font_rpm_sz, QFont.Weight.Bold))
        painter.setPen(COLOR_MINT_BRIGHT)
        painter.drawText(QRectF(w * 0.52, spd_y + (spd_h * 0.52), w * 0.44, spd_h * 0.40), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{self.motor_rpm} RPM")

        # Slim Speed Progress Bar
        bar_y = spd_y + spd_h + 2.0
        bar_w = w - 24.0
        bar_h = max(4.0, min(7.0, content_h * 0.05))

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(12, bar_y, bar_w, bar_h), 2, 2)

        spd_ratio = max(0.0, min(1.0, self.speed / max(1.0, self.max_speed)))
        painter.setBrush(QBrush(COLOR_MINT))
        painter.drawRoundedRect(QRectF(12, bar_y, bar_w * spd_ratio, bar_h), 2, 2)

        # Bottom Mini Pedals & Steer Pod
        sub_y = h - max(26.0, min(36.0, h * 0.20))
        sub_h = h - sub_y - 6.0
        sub_rect = QRectF(10, sub_y, w - 20, sub_h)
        painter.setBrush(QBrush(QColor(6, 14, 10, 190)))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
        painter.drawRoundedRect(sub_rect, 4, 4)

        font_pedal = QFont("Consolas", max(6, min(9, int(sub_h * 0.36))), QFont.Weight.Bold)
        painter.setFont(font_pedal)

        col_w = (w - 28.0) / 3.0
        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(12, sub_y, col_w, sub_h), Qt.AlignmentFlag.AlignCenter, f"THR {int(self.throttle_pct)}%")
        painter.setPen(COLOR_RED if self.brake_pct > 0 else COLOR_TEXT_MUTED)
        painter.drawText(QRectF(12 + col_w, sub_y, col_w, sub_h), Qt.AlignmentFlag.AlignCenter, f"BRK {int(self.brake_pct)}%")
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(QRectF(12 + 2 * col_w, sub_y, col_w, sub_h), Qt.AlignmentFlag.AlignCenter, f"STR {int(self.steer_angle)}°")

        painter.end()


class BatteryHeroWidget(QWidget):
    """
    Magnified Center Stage Hero View for High-Voltage Battery & Energy Diagnostics.
    Features large Cyber-Mint SoC Arc, Estimated Range HUD, and 4-Quadrant Diagnostic Grid.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.soc = 88.5
        self.voltage = 398.4
        self.current = 145.2
        self.power_kw = 57.8
        self.est_range_km = 372.0
        self.unit_system = "IMPERIAL"
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(220)

    def set_unit_system(self, unit_system: str) -> None:
        self.unit_system = unit_system
        self.update()

    def set_battery_data(
        self,
        soc: float,
        voltage: float,
        current: float,
        power_kw: float,
        est_range_km: Optional[float] = None,
        trip_km: Optional[float] = None,
        unit_system: str = "IMPERIAL",
    ) -> None:
        self.soc = max(0.0, min(100.0, soc))
        self.voltage = voltage
        self.current = current
        self.power_kw = power_kw
        if est_range_km is not None:
            self.est_range_km = est_range_km
        else:
            self.est_range_km = (self.soc / 100.0) * 420.0
        self.unit_system = unit_system
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 10, 10)

        # Header: clean responsive text
        hdr_font_sz = max(7, min(10, int(w * 0.028)))
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        title_str = "⚡ BATTERY & ENERGY" if w < 380 else "⚡ HIGH-VOLTAGE BATTERY & ENERGY"
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(QRectF(14, 8, w * 0.55, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_str)

        status_str = "● DISCHARGING" if self.current > 5.0 else ("● REGEN" if self.current < -2.0 else "● STANDBY")
        s_color = COLOR_AMBER if self.current > 70.0 else (COLOR_CYAN if self.current < -2.0 else COLOR_MINT)
        painter.setPen(s_color)
        painter.drawText(QRectF(w * 0.50, 8, w * 0.50 - 14, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, status_str)

        content_h = h - 30.0

        # Upper Area: Left SoC Arc + Range HUD, Right Pack Diagnostics Chips
        upper_h = content_h * 0.52
        upper_y = 30.0

        # Left Section: SoC Arc
        arc_cx = max(65.0, w * 0.16)
        arc_r = min(w * 0.11, upper_h * 0.44)
        arc_cy = upper_y + (upper_h * 0.48)
        arc_rect = QRectF(arc_cx - arc_r, arc_cy - arc_r, arc_r * 2, arc_r * 2)

        start_ang = 210.0
        span_ang = -240.0
        pen_w = max(4.0, min(8.0, arc_r * 0.18))

        # Track
        painter.setPen(QPen(COLOR_GAUGE_TRACK, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(arc_rect, int(start_ang * 16), int(span_ang * 16))

        # Active Arc
        bar_color = COLOR_MINT if self.soc > 30.0 else (COLOR_AMBER if self.soc > 15.0 else COLOR_RED)
        active_span = span_ang * (self.soc / 100.0)
        if self.soc > 0.5:
            painter.setPen(QPen(bar_color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(arc_rect, int(start_ang * 16), int(active_span * 16))

        # SoC Number
        font_soc_sz = max(13, min(24, int(arc_r * 0.42)))
        painter.setFont(QFont("Segoe UI", font_soc_sz, QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(QRectF(arc_cx - arc_r, arc_cy - (arc_r * 0.55), arc_r * 2, arc_r), Qt.AlignmentFlag.AlignCenter, f"{int(round(self.soc))}%")

        # Range HUD
        rng_x = arc_cx + arc_r + 14.0
        rng_w = max(100.0, (w * 0.46) - rng_x)
        rng_y = arc_cy - (arc_r * 0.65)

        painter.setFont(QFont("Segoe UI", max(6, min(9, int(upper_h * 0.10))), QFont.Weight.DemiBold))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(rng_x, rng_y, rng_w, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "ESTIMATED RANGE")

        is_imp = (self.unit_system == "IMPERIAL")
        range_val = int(round(self.est_range_km * 0.621371)) if is_imp else int(round(self.est_range_km))
        unit_str = "mi" if is_imp else "km"

        painter.setFont(QFont("Segoe UI", max(14, min(24, int(upper_h * 0.22))), QFont.Weight.Bold))
        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(rng_x, rng_y + 16, rng_w, 28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{range_val} {unit_str}")

        # Right Section: Pack Diagnostics Summary Grid (4 chips)
        right_start_x = max(w * 0.50, rng_x + rng_w + 10.0)
        right_w = w - right_start_x - 14.0
        chip_w = (right_w - 8.0) / 2.0
        chip_h = (upper_h - 14.0) / 2.0

        chips = [
            ("CELL AVG", "4.15 V", COLOR_MINT),
            ("HEALTH (SOH)", "100%", COLOR_MINT_BRIGHT),
            ("CHARGE LIMIT", "90%", COLOR_CYAN),
            ("PEAK TEMP", "32.0°C" if not is_imp else "89.6°F", COLOR_TEXT_PRIMARY),
        ]
        f_ch_lbl = QFont("Segoe UI", max(6, min(8, int(chip_h * 0.26))), QFont.Weight.Bold)
        f_ch_val = QFont("Consolas", max(7, min(11, int(chip_h * 0.38))), QFont.Weight.Bold)

        for idx, (title, val, color) in enumerate(chips):
            c_col = idx % 2
            c_row = idx // 2
            cx_pos = right_start_x + c_col * (chip_w + 8.0)
            cy_pos = upper_y + 6.0 + c_row * (chip_h + 6.0)

            c_rect = QRectF(cx_pos, cy_pos, chip_w, chip_h)
            painter.setBrush(QBrush(QColor(6, 14, 10, 190)))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
            painter.drawRoundedRect(c_rect, 4, 4)

            painter.setFont(f_ch_lbl)
            painter.setPen(COLOR_TEXT_MUTED)
            painter.drawText(QRectF(cx_pos + 6, cy_pos + 2, chip_w - 12, chip_h * 0.42), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

            painter.setFont(f_ch_val)
            painter.setPen(color)
            painter.drawText(QRectF(cx_pos + 6, cy_pos + chip_h * 0.38, chip_w - 12, chip_h * 0.58), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, val)

        # Bottom 4-Quadrant Diagnostic Grid
        grid_y = upper_y + upper_h + 4.0
        grid_h = h - grid_y - 8.0
        grid_w = w - 24.0

        quad_w = (grid_w - 8.0) / 2.0
        quad_h = (grid_h - 6.0) / 2.0

        quads = [
            ("PACK VOLTAGE", f"{self.voltage:.1f} V", COLOR_TEXT_PRIMARY, 0, 0),
            ("CURRENT DRAW", f"{self.current:+.1f} A", s_color, 1, 0),
            ("NET POWER", f"{self.power_kw:+.1f} kW", COLOR_CYAN if self.power_kw < 0 else COLOR_MINT_BRIGHT, 0, 1),
            ("CONSUMPTION", "15.2 kWh/100km" if not is_imp else "24.5 kWh/100mi", COLOR_TEXT_PRIMARY, 1, 1),
        ]

        f_q_lbl = QFont("Segoe UI", max(6, min(9, int(quad_h * 0.28))), QFont.Weight.Bold)
        f_q_val = QFont("Consolas", max(8, min(14, int(quad_h * 0.40))), QFont.Weight.Bold)

        for title, val, color, col, row in quads:
            qx = 12.0 + col * (quad_w + 8.0)
            qy = grid_y + row * (quad_h + 6.0)
            q_rect = QRectF(qx, qy, quad_w, quad_h)

            painter.setBrush(QBrush(QColor(6, 14, 10, 190)))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
            painter.drawRoundedRect(q_rect, 4, 4)

            painter.setFont(f_q_lbl)
            painter.setPen(COLOR_TEXT_MUTED)
            painter.drawText(QRectF(qx + 10, qy + 2, quad_w - 20, quad_h * 0.42), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

            painter.setFont(f_q_val)
            painter.setPen(color)
            painter.drawText(QRectF(qx + 10, qy + (quad_h * 0.38), quad_w - 20, quad_h * 0.58), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, val)

        painter.end()


class PowertrainHeroWidget(QWidget):
    """
    Magnified Center Stage Hero View for Dual-Motor AWD Powertrain Dynamics.
    Features large AWD Torque Split meters, Bidirectional Power Spectrum, and Live Waveform.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.front_pct = 42.0
        self.rear_pct = 58.0
        self.front_nm = 185.0
        self.rear_nm = 255.0
        self.bias_mode = "REAR BIAS"
        self.power_kw = 57.8
        self.max_kw = 120.0
        self.max_regen_kw = 60.0
        self.speed = 104.0
        self.unit_system = "IMPERIAL"
        self.wave_points: List[Tuple[float, float]] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(220)

    def set_unit_system(self, unit_system: str) -> None:
        self.unit_system = unit_system
        self.update()

    def set_powertrain_data(
        self,
        front_pct: float = 50.0,
        rear_pct: float = 50.0,
        front_nm: float = 0.0,
        rear_nm: float = 0.0,
        power_kw: float = 0.0,
        bias_mode: str = "AWD",
        speed_kmh: float = 0.0,
        f_pct: Optional[float] = None,
        r_pct: Optional[float] = None,
        f_nm: Optional[float] = None,
        r_nm: Optional[float] = None,
        bias: Optional[str] = None,
        pwr_kw: Optional[float] = None,
        spd: Optional[float] = None,
        unit_system: str = "IMPERIAL",
    ) -> None:
        self.front_pct = f_pct if f_pct is not None else front_pct
        self.rear_pct = r_pct if r_pct is not None else rear_pct
        self.front_nm = f_nm if f_nm is not None else front_nm
        self.rear_nm = r_nm if r_nm is not None else rear_nm
        self.bias_mode = bias if bias is not None else bias_mode
        self.power_kw = pwr_kw if pwr_kw is not None else power_kw
        self.speed = spd if spd is not None else speed_kmh
        self.unit_system = unit_system
        self.wave_points.append((self.speed, self.power_kw))
        if len(self.wave_points) > 50:
            self.wave_points.pop(0)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

        painter.setBrush(QBrush(COLOR_PANEL_BG))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 10, 10)

        # Header
        hdr_font_sz = max(7, min(10, int(w * 0.028)))
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        title_str = "⚡ POWERTRAIN DYNAMICS" if w < 380 else "⚡ DUAL-MOTOR AWD POWERTRAIN"
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(QRectF(14, 8, w * 0.58, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_str)

        bias_str = f"● {self.bias_mode.replace('AWD ', '')}"
        painter.setPen(COLOR_MINT_BRIGHT)
        painter.drawText(QRectF(w * 0.52, 8, w * 0.48 - 14, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, bias_str)

        content_h = h - 30.0

        # 1. AWD Torque Split Section (Upper 32%)
        sec1_y = 30.0
        sec1_h = content_h * 0.28

        is_imp = (self.unit_system == "IMPERIAL")
        t_unit = "lb-ft" if is_imp else "Nm"
        f_val = int(self.front_nm * 0.73756) if is_imp else int(self.front_nm)
        r_val = int(self.rear_nm * 0.73756) if is_imp else int(self.rear_nm)

        lbl_font = QFont("Segoe UI", max(7, min(9, int(sec1_h * 0.24))), QFont.Weight.Bold)
        val_font = QFont("Consolas", max(7, min(9, int(sec1_h * 0.24))), QFont.Weight.Bold)

        # Front Row
        y_f = sec1_y + (sec1_h * 0.22)
        painter.setFont(lbl_font)
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(QRectF(14, y_f - 8, 48, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "FRONT")

        bar_l = 66.0
        val_w = 90.0
        bar_w = w - bar_l - val_w - 14.0
        bar_h = max(5.0, min(8.0, sec1_h * 0.16))

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_l, y_f - 4, bar_w, bar_h), 2.5, 2.5)

        painter.setBrush(QBrush(COLOR_MINT))
        painter.drawRoundedRect(QRectF(bar_l, y_f - 4, bar_w * (self.front_pct / 100.0), bar_h), 2.5, 2.5)

        painter.setFont(val_font)
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(QRectF(w - val_w - 14, y_f - 8, val_w, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{int(self.front_pct)}% {f_val} {t_unit}")

        # Rear Row
        y_r = sec1_y + (sec1_h * 0.68)
        painter.setFont(lbl_font)
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(QRectF(14, y_r - 8, 48, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "REAR")

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_l, y_r - 4, bar_w, bar_h), 2.5, 2.5)

        painter.setBrush(QBrush(COLOR_MINT_BRIGHT if self.rear_pct < 65.0 else COLOR_AMBER))
        painter.drawRoundedRect(QRectF(bar_l, y_r - 4, bar_w * (self.rear_pct / 100.0), bar_h), 2.5, 2.5)

        painter.setFont(val_font)
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(QRectF(w - val_w - 14, y_r - 8, val_w, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{int(self.rear_pct)}% {r_val} {t_unit}")

        # 2. Bidirectional Power / Regen Bar (Middle 22%)
        sec2_y = sec1_y + sec1_h + 2.0
        sec2_h = content_h * 0.22

        pwr_bar_w = w - 28.0
        pwr_bar_h = max(6.0, min(10.0, sec2_h * 0.25))
        pwr_bar_y = sec2_y + 14.0

        painter.setFont(QFont("Segoe UI", max(6, min(8, int(sec2_h * 0.20))), QFont.Weight.Bold))
        painter.setPen(COLOR_CYAN)
        painter.drawText(QRectF(14, sec2_y, 80, 12), Qt.AlignmentFlag.AlignLeft, "REGEN -60kW")
        painter.setPen(COLOR_AMBER)
        painter.drawText(QRectF(w - 94, sec2_y, 80, 12), Qt.AlignmentFlag.AlignRight, "+120kW PWR")

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(14, pwr_bar_y, pwr_bar_w, pwr_bar_h), 2.5, 2.5)

        # Center Zero Mark
        total_range = self.max_regen_kw + self.max_kw
        zero_x = 14.0 + (pwr_bar_w * (self.max_regen_kw / total_range))

        painter.setPen(QPen(COLOR_TEXT_MUTED, 1.5))
        painter.drawLine(int(zero_x), int(pwr_bar_y - 2), int(zero_x), int(pwr_bar_y + pwr_bar_h + 2))

        # Active Fill
        if self.power_kw < -0.2:
            fill_w = (abs(self.power_kw) / self.max_regen_kw) * (zero_x - 14.0)
            fill_x = zero_x - fill_w
            painter.setBrush(QBrush(COLOR_CYAN))
            painter.drawRoundedRect(QRectF(fill_x, pwr_bar_y, fill_w, pwr_bar_h), 2, 2)
        elif self.power_kw > 0.2:
            fill_w = (self.power_kw / self.max_kw) * (14.0 + pwr_bar_w - zero_x)
            painter.setBrush(QBrush(COLOR_MINT if self.power_kw < 70.0 else COLOR_AMBER))
            painter.drawRoundedRect(QRectF(zero_x, pwr_bar_y, fill_w, pwr_bar_h), 2, 2)

        # Readout below bar
        painter.setFont(QFont("Consolas", max(7, min(10, int(sec2_h * 0.26))), QFont.Weight.Bold))
        painter.setPen(COLOR_MINT_BRIGHT)
        painter.drawText(QRectF(w * 0.30, pwr_bar_y + pwr_bar_h + 2, w * 0.40, 14), Qt.AlignmentFlag.AlignCenter, f"{self.power_kw:+.1f} kW")

        # 3. Live Rolling Telemetry Waveform (Bottom 44%)
        sec3_y = sec2_y + sec2_h + 4.0
        sec3_h = h - sec3_y - 8.0
        wave_rect = QRectF(14, sec3_y, w - 28, sec3_h)

        painter.setBrush(QBrush(QColor(6, 14, 10, 190)))
        painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
        painter.drawRoundedRect(wave_rect, 4, 4)

        painter.setFont(QFont("Segoe UI", max(6, min(8, int(sec3_h * 0.15))), QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(20, sec3_y + 4, 120, 14), Qt.AlignmentFlag.AlignLeft, "LIVE TELEMETRY WAVE")

        painter.setPen(COLOR_MINT)
        painter.drawText(QRectF(w - 96, sec3_y + 4, 34, 14), Qt.AlignmentFlag.AlignRight, "SPD")
        painter.setPen(COLOR_AMBER)
        painter.drawText(QRectF(w - 56, sec3_y + 4, 34, 14), Qt.AlignmentFlag.AlignRight, "PWR")

        # Draw Grid Line
        mid_y = sec3_y + (sec3_h * 0.55)
        painter.setPen(QPen(QColor(18, 50, 38, 120), 1, Qt.PenStyle.DashLine))
        painter.drawLine(int(18), int(mid_y), int(w - 18), int(mid_y))

        # Plot Waves if points exist
        if len(self.wave_points) > 1:
            step_x = (w - 36.0) / max(1, len(self.wave_points) - 1)
            spd_poly = QPolygonF()
            pwr_poly = QPolygonF()

            for idx, (spd_val, pwr_val) in enumerate(self.wave_points):
                px = 18.0 + idx * step_x
                py_spd = (sec3_y + sec3_h - 6.0) - (spd_val / 180.0) * (sec3_h - 24.0)
                spd_poly.append(QPointF(px, max(sec3_y + 18.0, min(sec3_y + sec3_h - 4.0, py_spd))))

                py_pwr = (sec3_y + sec3_h - 6.0) - ((pwr_val + 60.0) / 180.0) * (sec3_h - 24.0)
                pwr_poly.append(QPointF(px, max(sec3_y + 18.0, min(sec3_y + sec3_h - 4.0, py_pwr))))

            painter.setPen(QPen(COLOR_MINT, 1.8))
            painter.drawPolyline(spd_poly)

            painter.setPen(QPen(COLOR_AMBER, 1.8))
            painter.drawPolyline(pwr_poly)

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

    hero_view_changed = pyqtSignal(str)          # "SPEED", "BATTERY", "POWERTRAIN"
    wing_swap_changed = pyqtSignal(bool)         # True if swapped

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voltesse Dash - Digital Cockpit")
        # Leave room for the cockpit on smaller embedded displays. The layout
        # itself scales to the available size, including 800x480 panels.
        self.setMinimumSize(400, 240)
        # Adapt default window size to detected display (800x480 on compact screens)
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            init_w = geom.width() if geom.width() > 0 else 800
            init_h = geom.height() if geom.height() > 0 else 480
            if init_w <= 1024 or init_h <= 600:
                self.resize(init_w, init_h)
            else:
                self.resize(1280, 720)
        else:
            self.resize(800, 480)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.BlankCursor)

        # Active operating mode state
        self.current_mode = "RACE"
        self.current_transmission = "AUTO"
        self.unit_system = "IMPERIAL"
        self.user_scale_multiplier = 1.0
        self.current_page_idx = 0
        self.active_hero_view = "SPEED"
        self.swap_wings = False
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
        self.top_bar.setStyleSheet("background-color: rgba(4, 12, 8, 0.65); border-bottom: 1px solid rgba(0, 245, 160, 0.2); border-radius: 4px;")
        self.top_layout = QHBoxLayout(self.top_bar)
        self.top_layout.setContentsMargins(10, 0, 10, 0)
        self.top_layout.setSpacing(10)

        # Turn Signal Left
        self.left_blinker = QLabel("◄")
        self.left_blinker.setStyleSheet("color: #123226;")

        # Brand / Subtitle
        self.brand_label = QLabel("⚡ VOLTESSE")
        self.brand_label.setStyleSheet("color: #00F5A0; letter-spacing: 2px;")

        # Compact Digital Speed Pill (Always visible when away from Speedometer page)
        self.speed_hud_badge = QLabel("0 MPH [D1]")
        self.speed_hud_badge.setStyleSheet(
            "color: #00F5A0; background-color: rgba(0, 245, 160, 0.18); border: 1px solid #00F5A0; "
            "padding: 2px 8px; border-radius: 4px; font-weight: bold; font-family: Consolas; font-size: 8.5pt;"
        )
        self.speed_hud_badge.setVisible(False)

        # Legacy badges preserved as attributes for backward compatibility but hidden from active top bar
        self.ready_badge = QLabel("READY")
        self.ready_badge.setVisible(False)
        self.logging_badge = QLabel("REC")
        self.logging_badge.setVisible(False)
        self.units_badge = QLabel("IMPERIAL")
        self.units_badge.setVisible(False)
        self.op_mode_badge = QLabel("RACE [CAN]")
        self.op_mode_badge.setVisible(False)
        self.trans_mode_badge = QLabel("AUTO [D1]")
        self.trans_mode_badge.setVisible(False)
        self.controls_hint = QLabel("")
        self.controls_hint.setVisible(False)

        # Interactive Page Navigator Pill with clickable Left/Right buttons
        self.nav_frame = QFrame()
        self.nav_frame.setStyleSheet("background-color: rgba(12, 26, 20, 0.9); border: 1px solid rgba(0, 245, 160, 0.35); border-radius: 4px;")
        nav_layout = QHBoxLayout(self.nav_frame)
        nav_layout.setContentsMargins(4, 1, 4, 1)
        nav_layout.setSpacing(6)

        self.nav_prev_btn = QPushButton("◄")
        self.nav_prev_btn.setFixedSize(20, 20)
        self.nav_prev_btn.setStyleSheet("QPushButton { color: #00F5A0; background: transparent; border: none; font-weight: bold; font-size: 10pt; } QPushButton:hover { color: #FFFFFF; }")
        self.nav_prev_btn.clicked.connect(self.prev_page)
        nav_layout.addWidget(self.nav_prev_btn)

        self.page_title_label = QLabel("PAGE 1/4: SPEED")
        self.page_title_label.setStyleSheet("color: #00F5A0; font-weight: bold; font-size: 8pt; font-family: 'Segoe UI';")
        nav_layout.addWidget(self.page_title_label)

        self.nav_next_btn = QPushButton("►")
        self.nav_next_btn.setFixedSize(20, 20)
        self.nav_next_btn.setStyleSheet("QPushButton { color: #00F5A0; background: transparent; border: none; font-weight: bold; font-size: 10pt; } QPushButton:hover { color: #FFFFFF; }")
        self.nav_next_btn.clicked.connect(self.next_page)
        nav_layout.addWidget(self.nav_next_btn)

        # Hero View Status Badge alias
        self.view_badge = self.page_title_label

        # Drive Mode Pill (ECO / DRIVE / SPORT)
        self.mode_badge = QLabel("SPORT")
        self.mode_badge.setStyleSheet(
            "background-color: rgba(255, 77, 109, 0.2); color: #FF4D6D; padding: 2px 10px; border-radius: 4px; border: 1px solid rgba(255, 77, 109, 0.5); font-weight: bold;"
        )

        self._update_op_mode_badge_style("RACE")

        # Status / Warning Pill (Only visible when active vehicle alert exists)
        self.status_badge = QLabel("")
        self.status_badge.setStyleSheet(
            "background-color: rgba(0, 245, 160, 0.12); color: #5CFFC7; padding: 2px 8px; border-radius: 4px;"
        )
        self.status_badge.setMinimumWidth(0)
        self.status_badge.setVisible(False)
        self.top_bar.setMinimumWidth(0)

        # Ambient Temp
        self.ambient_label = QLabel("72°F")
        self.ambient_label.setStyleSheet("color: #9AE6B4;")

        # Live Clock
        self.clock_label = QLabel("12:00:00 AM")
        self.clock_label.setStyleSheet("color: #FFFFFF;")

        # Turn Signal Right
        self.right_blinker = QLabel("►")
        self.right_blinker.setStyleSheet("color: #123226;")

        # Streamlined, distraction-free Top Layout
        self.top_layout.addWidget(self.left_blinker)
        self.top_layout.addWidget(self.brand_label)
        self.top_layout.addWidget(self.speed_hud_badge)
        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.nav_frame)
        self.top_layout.addWidget(self.status_badge)
        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.mode_badge)
        self.top_layout.addWidget(self.ambient_label)
        self.top_layout.addWidget(self.clock_label)
        self.top_layout.addWidget(self.right_blinker)

        self.main_layout.addWidget(self.top_bar)

        # -------------------------------------------------------------
        # 2. MAIN COCKPIT CENTRAL STAGE (Full-Width Single Widget Stack)
        # -------------------------------------------------------------
        self.page_stack = QStackedWidget()
        self.page_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Page 0: Full-Width Speedometer Dial (MPH)
        self.speed_page = SpeedometerDialWidget(min_val=0.0, max_val=120.0, title="SPEED", unit="MPH")
        self.page_stack.addWidget(self.speed_page)      # Index 0

        # Page 1: Full-Width Battery & Energy Diagnostics
        self.battery_page = BatteryHeroWidget()
        self.page_stack.addWidget(self.battery_page)    # Index 1

        # Page 2: Full-Width Powertrain Dynamics & AWD
        self.powertrain_page = PowertrainHeroWidget()
        self.page_stack.addWidget(self.powertrain_page) # Index 2

        # Page 3: Full-Width 4-Wheel TPMS Monitoring
        self.tpms_page = TPMSWidget()
        self.page_stack.addWidget(self.tpms_page)       # Index 3

        self.main_layout.addWidget(self.page_stack, stretch=1)

        # Aliases for core widgets
        self.center_stack = self.page_stack
        self.speed_gauge = self.speed_page
        self.battery_hero = self.battery_page
        self.powertrain_hero = self.powertrain_page
        self.tpms_widget = self.tpms_page

        # Preserved widgets and dummy hierarchies for legacy telemetry / test assertions
        self.compact_speed_widget = CompactSpeedPod()
        self.battery_widget = BatteryStatusWidget()
        self.battery_widget_alt = BatteryStatusWidget()
        self.awd_widget = AwdTorqueVectorWidget()
        self.power_bar = PowerBarWidget()
        self.sparkline_widget = LiveSparklineWidget(max_points=50)
        self.sparkline_widget_alt = LiveSparklineWidget(max_points=50)

        self.wing_1 = QFrame()
        self.wing_1_layout = QVBoxLayout(self.wing_1)
        self.wing_1_top_stack = QStackedWidget()
        self.wing_1_top_stack.addWidget(self.battery_widget)
        self.wing_1_top_stack.addWidget(self.compact_speed_widget)

        self.wing_2 = QFrame()
        self.wing_2_layout = QVBoxLayout(self.wing_2)
        self.wing_2_stack = QStackedWidget()
        dummy_dyn = QWidget()
        self.wing_2_stack.addWidget(dummy_dyn)
        dummy_pwr = QWidget()
        self.wing_2_stack.addWidget(dummy_pwr)

        self.left_wing = self.wing_1
        self.left_wing_layout = self.wing_1_layout
        self.right_wing = self.wing_2
        self.right_wing_layout = self.wing_2_layout

        self.stage_layout = QHBoxLayout()
        self.center_stage = QFrame()
        self.stage_layout.addWidget(self.wing_1, stretch=3)
        self.stage_layout.addWidget(self.center_stage, stretch=4)
        self.stage_layout.addWidget(self.wing_2, stretch=3)

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

        self.power_pod = QFrame()
        self.right_hdr = QLabel("⚡ POWERTRAIN DYNAMICS")
        self.power_title = QLabel("NET POWER")
        self.power_val = QLabel("0.0 kW")
        self.pedal_frame = QFrame()
        self.throttle_label = QLabel("THR: 0%")
        self.brake_label = QLabel("BRK: 0%")

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

        self.trip_dist_val = QLabel("0.00 mi")
        self.trip_dist_val.setStyleSheet("color: #FFFFFF; border: none; background: transparent;")

        self.trip_layout.addWidget(self.trip_hdr)
        self.trip_layout.addWidget(self.trip_dist_val)
        self.bottom_layout.addWidget(self.trip_pod)

        # Thermal Diagnostics Pods
        self.thermal_widget = ThermalMonitorWidget()
        self.bottom_layout.addWidget(self.thermal_widget, stretch=1)

        self.main_layout.addWidget(self.bottom_bar)

        # Allow proportional scaling without rigid minimum width locks
        for w in [
            self.wing_1, self.left_wing, self.center_stage, self.wing_2, self.right_wing, self.power_pod,
        ]:
            w.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
            w.setMinimumWidth(0)

        for w in [
            self.right_hdr, self.power_title, self.power_val, self.throttle_label, self.brake_label,
            self.pedal_frame, self.top_bar, self.bottom_bar, self.brand_label, self.ready_badge,
            self.logging_badge, self.units_badge, self.view_badge, self.op_mode_badge, self.trans_mode_badge,
            self.mode_badge, self.status_badge, self.ambient_label, self.clock_label,
            self.controls_hint, self.trip_pod, self.trip_hdr, self.trip_dist_val,
            self.thermal_widget, self.battery_widget, self.tpms_widget, self.awd_widget,
            self.sparkline_widget, self.speed_gauge, self.left_blinker, self.right_blinker,
            self.wing_1_top_stack, self.wing_2_stack, self.center_stack, self.compact_speed_widget,
            self.battery_hero, self.powertrain_hero, self.battery_widget_alt, self.sparkline_widget_alt,
        ]:
            w.setMinimumWidth(0)

        self._apply_dynamic_scale()

    def set_user_scale(self, multiplier: float) -> None:
        """Sets an explicit UI zoom scale factor (e.g. 0.85 for denser display, 1.0 for default)."""
        self.user_scale_multiplier = max(0.35, min(2.0, float(multiplier)))
        self._apply_dynamic_scale()

    def mousePressEvent(self, event) -> None:
        """Ensures cockpit window maintains primary keyboard focus upon clicks."""
        self.setFocus()
        super().mousePressEvent(event)

    def _apply_dynamic_scale(self) -> None:
        """Dynamically adjusts font sizes and spacings for crisp proportions across resolutions."""
        w = max(1, self.width())
        h = max(1, self.height())

        raw_scale = min(w / 1280.0, h / 720.0)
        # On compact embedded screens (e.g. 800x480 Raspberry Pi), use a denser reference
        # (1440x840) so all gauges, numbers, and pods have comfortable breathing room.
        if w <= 950 or h <= 540:
            base_scale = min(w / 1440.0, h / 840.0)
        else:
            base_scale = raw_scale

        user_mult = getattr(self, "user_scale_multiplier", 1.0)
        scale = max(0.30, min(2.0, base_scale * user_mult))

        # Compact chrome margins tailored for 800x480 and variable displays
        margin_x = max(2, int(8 * scale))
        margin_top = max(2, int(4 * scale))
        margin_bottom = max(2, int(4 * scale))
        self.main_layout.setContentsMargins(margin_x, margin_top, margin_x, margin_bottom)
        self.main_layout.setSpacing(max(2, int(4 * scale)))
        self.top_layout.setContentsMargins(max(4, int(8 * scale)), 0, max(4, int(8 * scale)), 0)
        self.top_layout.setSpacing(max(2, int(4 * scale)))
        self.stage_layout.setSpacing(max(3, int(6 * scale)))
        self.left_wing_layout.setSpacing(max(2, int(5 * scale)))
        self.right_wing_layout.setSpacing(max(2, int(5 * scale)))
        self.bottom_layout.setSpacing(max(2, int(5 * scale)))

        top_h = max(34, min(56, int(42 * scale)))
        self.top_bar.setFixedHeight(top_h)

        bot_h = max(32, min(64, int(44 * scale)))
        self.bottom_bar.setFixedHeight(bot_h)

        self.trip_pod.setFixedWidth(max(85, min(220, int(140 * scale))))

        # Streamline top ribbon: hide useless clutter badges
        self.controls_hint.setVisible(False)
        self.ready_badge.setVisible(False)
        self.logging_badge.setVisible(False)
        self.units_badge.setVisible(False)
        self.op_mode_badge.setVisible(False)
        self.trans_mode_badge.setVisible(False)

        # Warning pill only visible when active alert exists
        has_warnings = bool(hasattr(self, "_last_record") and self._last_record and self._last_record.warnings)
        self.status_badge.setVisible(has_warnings)

        # Dynamic text compactness on smaller displays
        if w < 950:
            self.right_hdr.setText("⚡ POWERTRAIN")
            self.power_title.setText("NET PWR")
            self.trip_hdr.setText("TRIP")
        else:
            self.right_hdr.setText("⚡ POWERTRAIN DYNAMICS")
            self.power_title.setText("NET POWER")
            self.trip_hdr.setText("TRIP ODOMETER")

        # Dynamic badge styling with proportional padding and radii
        pad_y = max(1, int(2 * scale))
        pad_x = max(2, int(6 * scale))
        b_rad = max(2, int(4 * scale))
        self.ready_badge.setStyleSheet(
            f"color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: {pad_y}px {pad_x}px; border-radius: {b_rad}px; border: 1px solid rgba(0, 245, 160, 0.4);"
        )
        self.logging_badge.setStyleSheet(
            f"color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: {pad_y}px {pad_x}px; border-radius: {b_rad}px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
        )
        self.units_badge.setStyleSheet(
            f"color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: {pad_y}px {pad_x}px; border-radius: {b_rad}px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
        )
        self.view_badge.setStyleSheet(
            f"color: #00F5A0; background-color: rgba(0, 245, 160, 0.15); padding: {pad_y}px {pad_x}px; border-radius: {b_rad}px; border: 1px solid rgba(0, 245, 160, 0.4); font-weight: bold;"
        )
        self.trans_mode_badge.setStyleSheet(
            f"background-color: rgba(0, 245, 160, 0.15); color: #5CFFC7; padding: {pad_y}px {pad_x}px; border-radius: {b_rad}px; border: 1px solid rgba(0, 245, 160, 0.4);"
        )
        self.mode_badge.setStyleSheet(
            f"background-color: rgba(0, 245, 160, 0.15); color: #5CFFC7; padding: {pad_y}px {pad_x}px; border-radius: {b_rad}px; border: 1px solid rgba(0, 245, 160, 0.4);"
        )
        self.status_badge.setStyleSheet(
            f"background-color: rgba(0, 245, 160, 0.12); color: #5CFFC7; padding: {pad_y}px {pad_x}px; border-radius: {b_rad}px;"
        )

        f_brand = QFont("Segoe UI", max(9, min(18, int(12 * scale))), QFont.Weight.Black)
        self.brand_label.setFont(f_brand)

        f_hud = QFont("Segoe UI", max(7, min(13, int(8.5 * scale))), QFont.Weight.Bold)
        self.ready_badge.setFont(f_hud)
        self.logging_badge.setFont(f_hud)
        self.units_badge.setFont(f_hud)
        self.view_badge.setFont(f_hud)
        self.op_mode_badge.setFont(f_hud)
        self.trans_mode_badge.setFont(f_hud)
        self.mode_badge.setFont(f_hud)
        self.status_badge.setFont(f_hud)

        f_hint = QFont("Consolas", max(7, min(11, int(8 * scale))), QFont.Weight.Normal)
        self.controls_hint.setFont(f_hint)

        f_clock = QFont("Consolas", max(8, min(15, int(11 * scale))), QFont.Weight.Bold)
        self.clock_label.setFont(f_clock)
        self.ambient_label.setFont(f_clock)

        f_blinker = QFont("Segoe UI", max(9, min(16, int(11 * scale))), QFont.Weight.Bold)
        self.left_blinker.setFont(f_blinker)
        self.right_blinker.setFont(f_blinker)

        f_hdrs = QFont("Segoe UI", max(7, min(13, int(8.5 * scale))), QFont.Weight.Bold)
        self.right_hdr.setFont(f_hdrs)
        self.power_title.setFont(f_hdrs)

        f_lbl = QFont("Segoe UI", max(6, min(10, int(7 * scale))), QFont.Weight.Bold)
        self.trip_hdr.setFont(f_lbl)

        f_val = QFont("Consolas", max(7, min(14, int(9.5 * scale))), QFont.Weight.Bold)
        self.throttle_label.setFont(f_val)
        self.brake_label.setFont(f_val)
        self.trip_dist_val.setFont(QFont("Consolas", max(8, min(16, int(11 * scale))), QFont.Weight.Bold))

        f_pwr = QFont("Consolas", max(10, min(22, int(15 * scale))), QFont.Weight.Bold)
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
            self.controls_hint.setText("[KEYS: 1:RACE | 2:SIM | 3:TEST | V:VIEW | X:SWAP | T:TRANS | E/C:SHIFT | U:UNITS | L:LOG]")
        elif mode == "SIMULATION":
            self.op_mode_badge.setText("SIMULATION [GAME]")
            self.op_mode_badge.setStyleSheet(
                "background-color: rgba(0, 229, 255, 0.22); color: #00E5FF; padding: 2px 10px; border-radius: 4px; border: 1px solid #00E5FF; font-weight: bold;"
            )
            self.controls_hint.setText("[V:VIEW | X:SWAP | T:TRANS | W/S:PEDALS | A/D:STEER | E/C:SHIFT | U:UNITS | L:LOG | M:MODE]")
        elif mode == "TEST":
            self.op_mode_badge.setText("TEST [MOCK]")
            self.op_mode_badge.setStyleSheet(
                "background-color: rgba(154, 230, 180, 0.20); color: #5CFFC7; padding: 2px 10px; border-radius: 4px; border: 1px solid #5CFFC7; font-weight: bold;"
            )
            self.controls_hint.setText("[TEST: AUTO ONLY | V:VIEW | X:SWAP | 1:RACE | 2:SIM | U:UNITS | L:LOG | SPACE:PAUSE]")

    PAGE_NAMES = ["SPEED", "BATTERY", "POWERTRAIN", "TPMS"]

    def set_page(self, index: int) -> None:
        """Sets the active full-width page in the main cluster stack."""
        self.current_page_idx = index % len(self.PAGE_NAMES)
        self.page_stack.setCurrentIndex(self.current_page_idx)
        p_name = self.PAGE_NAMES[self.current_page_idx]
        self.active_hero_view = p_name

        swap_suffix = " [⇄]" if self.swap_wings else ""
        self.page_title_label.setText(f"◄ {p_name} [{self.current_page_idx+1}/4]{swap_suffix} ►")

        if p_name == "SPEED":
            self.nav_frame.setStyleSheet("background-color: rgba(12, 26, 20, 0.9); border: 1px solid rgba(0, 245, 160, 0.4); border-radius: 4px;")
            self.page_title_label.setStyleSheet("color: #00F5A0; font-weight: bold; font-size: 8pt;")
            self.speed_hud_badge.setVisible(False)
            self.ready_badge.setVisible(False)
            self.wing_1_top_stack.setCurrentIndex(0)
            self.wing_2_stack.setCurrentIndex(0)
        elif p_name == "BATTERY":
            self.nav_frame.setStyleSheet("background-color: rgba(6, 20, 26, 0.9); border: 1px solid rgba(0, 229, 255, 0.5); border-radius: 4px;")
            self.page_title_label.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 8pt;")
            self.speed_hud_badge.setVisible(True)
            self.ready_badge.setVisible(False)
            self.wing_1_top_stack.setCurrentIndex(1)
            self.wing_2_stack.setCurrentIndex(0)
        elif p_name == "POWERTRAIN":
            self.nav_frame.setStyleSheet("background-color: rgba(26, 20, 6, 0.9); border: 1px solid rgba(255, 184, 0, 0.5); border-radius: 4px;")
            self.page_title_label.setStyleSheet("color: #FFB800; font-weight: bold; font-size: 8pt;")
            self.speed_hud_badge.setVisible(True)
            self.ready_badge.setVisible(False)
            self.wing_1_top_stack.setCurrentIndex(1)
            self.wing_2_stack.setCurrentIndex(1)
        elif p_name == "TPMS":
            self.nav_frame.setStyleSheet("background-color: rgba(12, 26, 20, 0.9); border: 1px solid rgba(92, 255, 199, 0.4); border-radius: 4px;")
            self.page_title_label.setStyleSheet("color: #5CFFC7; font-weight: bold; font-size: 8pt;")
            self.speed_hud_badge.setVisible(True)
            self.ready_badge.setVisible(False)
            self.wing_1_top_stack.setCurrentIndex(1)
            self.wing_2_stack.setCurrentIndex(0)

        if hasattr(self, "_last_record") and self._last_record is not None:
            self.update_telemetry(self._last_record)

        self.hero_view_changed.emit(self.active_hero_view)

    def next_page(self) -> None:
        """Navigates to the next widget page (Right)."""
        self.set_page(self.current_page_idx + 1)

    def prev_page(self) -> None:
        """Navigates to the previous widget page (Left)."""
        self.set_page(self.current_page_idx - 1)

    def set_hero_view(self, view_name: str) -> None:
        """Sets the active widget page in the central stack by name."""
        v = view_name.upper().strip()
        mapping = {"SPEED": 0, "BATTERY": 1, "BATT": 1, "POWERTRAIN": 2, "PWR": 2, "TPMS": 3}
        self.set_page(mapping.get(v, 0))

    def cycle_hero_view(self) -> str:
        """Cycles to the next widget page."""
        self.next_page()
        return self.active_hero_view

    def toggle_wing_swap(self) -> bool:
        """Toggles the left and right wing layout positions."""
        self.set_wing_swap(not self.swap_wings)
        return self.swap_wings

    def set_wing_swap(self, swap: bool) -> None:
        """Sets whether left and right wings are swapped."""
        self.swap_wings = bool(swap)
        self.stage_layout.removeWidget(self.wing_1)
        self.stage_layout.removeWidget(self.center_stage)
        self.stage_layout.removeWidget(self.wing_2)

        if not self.swap_wings:
            self.stage_layout.addWidget(self.wing_1, stretch=3)
            self.stage_layout.addWidget(self.center_stage, stretch=4)
            self.stage_layout.addWidget(self.wing_2, stretch=3)
        else:
            self.stage_layout.addWidget(self.wing_2, stretch=3)
            self.stage_layout.addWidget(self.center_stage, stretch=4)
            self.stage_layout.addWidget(self.wing_1, stretch=3)

        self.set_page(self.current_page_idx)
        self.wing_swap_changed.emit(self.swap_wings)

    def toggle_units(self) -> str:
        """In v4.1.0, system is locked to IMPERIAL; returns active unit system."""
        self.set_unit_system("IMPERIAL")
        return "IMPERIAL"

    def set_unit_system(self, system: str = "IMPERIAL") -> None:
        """Enforces IMPERIAL system across all dashboard gauges and widgets."""
        self.unit_system = "IMPERIAL"
        self.units_badge.setText("IMPERIAL")
        self.ambient_label.setText("72°F")
        self.speed_gauge.set_units(unit="MPH", max_val=120.0)

        self.battery_widget.set_unit_system("IMPERIAL")
        self.tpms_widget.set_unit_system("IMPERIAL")
        self.thermal_widget.set_unit_system("IMPERIAL")
        self.awd_widget.set_unit_system("IMPERIAL")
        self.sparkline_widget.set_unit_system("IMPERIAL")
        self.compact_speed_widget.set_unit_system("IMPERIAL")
        self.battery_hero.set_unit_system("IMPERIAL")
        self.powertrain_hero.set_unit_system("IMPERIAL")
        self.battery_widget_alt.set_unit_system("IMPERIAL")
        self.sparkline_widget_alt.set_unit_system("IMPERIAL")

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

        is_imp = True
        disp_speed = record.speed_kmh * 0.621371

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

        # Compact Speed Pod (for non-speed hero views)
        self.compact_speed_widget.set_speed_and_status(
            disp_speed,
            gear=gear,
            rpm=record.motor_rpm,
            throttle=record.throttle_pct,
            brake=record.brake_pct,
            steering_angle=record.steering_angle,
            transmission_mode=trans_mode,
            unit="MPH",
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

        # Compact Speed HUD Badge in Top Ribbon (Visible when away from Speedometer page)
        self.speed_hud_badge.setText(f"{int(round(disp_speed))} MPH [{display_gear}]")

        # Battery & Voltage
        self.battery_widget.set_battery_data(
            record.battery_soc, record.battery_voltage, record.battery_current
        )
        self.battery_widget_alt.set_battery_data(
            record.battery_soc, record.battery_voltage, record.battery_current
        )
        self.battery_hero.set_battery_data(
            soc=record.battery_soc,
            voltage=record.battery_voltage,
            current=record.battery_current,
            power_kw=record.battery_power_kw,
            trip_km=record.trip_distance_km,
            unit_system="IMPERIAL",
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
            self.status_badge.setVisible(True)
        else:
            self.status_badge.setText("SYSTEM READY")
            self.status_badge.setStyleSheet(
                "background-color: rgba(0, 245, 160, 0.12); color: #5CFFC7; padding: 2px 10px; border-radius: 4px;"
            )
            self.status_badge.setVisible(False)

        # Thermals
        self.thermal_widget.set_temperatures(
            record.motor_temp_c, record.inverter_temp_c, record.battery_temp_c
        )

        # Trip Odometer
        disp_dist = record.trip_distance_km * 0.621371
        self.trip_dist_val.setText(f"{disp_dist:.2f} mi")

        # Sparkline trace
        self.sparkline_widget.add_data_point(disp_speed, record.battery_power_kw)
        self.sparkline_widget_alt.add_data_point(disp_speed, record.battery_power_kw)

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
        self.powertrain_hero.set_powertrain_data(
            front_pct=f_pct,
            rear_pct=r_pct,
            front_nm=f_nm,
            rear_nm=r_nm,
            power_kw=record.battery_power_kw,
            bias_mode=bias_str,
            speed_kmh=record.speed_kmh,
        )

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
        steer_l = (Qt.Key.Key_A in self._held_keys)
        steer_r = (Qt.Key.Key_D in self._held_keys)
        self.simulation_input_changed.emit(thr, brk, steer_l, steer_r)

    def keyPressEvent(self, event) -> None:
        """Handles mode switching, auto/manual transmission, and video-game controls."""
        key = event.key()

        # Prevent OS auto-repeat for one-shot action hotkeys
        if event.isAutoRepeat():
            if key not in (
                Qt.Key.Key_W, Qt.Key.Key_Up,
                Qt.Key.Key_S, Qt.Key.Key_Down,
                Qt.Key.Key_A, Qt.Key.Key_D,
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
        elif key == Qt.Key.Key_V:
            self.next_page()
            return
        elif key == Qt.Key.Key_Left:
            self.prev_page()
            return
        elif key == Qt.Key.Key_Right:
            self.next_page()
            return
        elif key == Qt.Key.Key_X:
            self.toggle_wing_swap()
            return
        elif key == Qt.Key.Key_Space:
            self.pause_requested.emit()
            return

        # Real-time interactive UI zoom controls (- to zoom out, +/= to zoom in, 0 to reset)
        elif key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
            self.user_scale_multiplier = max(0.35, round(self.user_scale_multiplier - 0.05, 2))
            self._apply_dynamic_scale()
            self.status_badge.setText(f"ZOOM: {int(round(self.user_scale_multiplier * 100))}%")
            return
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.user_scale_multiplier = min(2.0, round(self.user_scale_multiplier + 0.05, 2))
            self._apply_dynamic_scale()
            self.status_badge.setText(f"ZOOM: {int(round(self.user_scale_multiplier * 100))}%")
            return
        elif key in (Qt.Key.Key_0, Qt.Key.Key_ParenRight) and not event.isAutoRepeat():
            self.user_scale_multiplier = 1.0
            self._apply_dynamic_scale()
            self.status_badge.setText("ZOOM: 100%")
            return

        # Video Game Driving Inputs (W/A/S/D and Arrow Keys Up/Down)
        if key in (
            Qt.Key.Key_W, Qt.Key.Key_Up,
            Qt.Key.Key_S, Qt.Key.Key_Down,
            Qt.Key.Key_A, Qt.Key.Key_D,
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
