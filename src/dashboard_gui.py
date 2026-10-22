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
from dataclasses import dataclass
import math
import time
from typing import Deque, List, Optional, Set, Tuple

from PyQt6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
    QLinearGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
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
# Modern Cyber-Mint & Voltesse Race Cockpit Color Palette
# =====================================================================
COLOR_BG_DARK = QColor("#030706")
COLOR_PANEL_BG = QColor(8, 18, 14, 230)
COLOR_PANEL_BORDER = QColor(18, 50, 38, 200)

# Mint Green Spectrum
COLOR_MINT = QColor("#00F5A0")           # Primary Neon Mint
COLOR_MINT_BRIGHT = QColor("#5CFFC7")    # Highlight Mint
COLOR_MINT_DIM = QColor(0, 245, 160, 45) # Subtle glow
COLOR_MINT_DARK = QColor("#00B374")      # Deep Mint / Emerald

# Secondary Accents & Race Telemetry
COLOR_CYAN = QColor("#00E5FF")           # Simulation Cyan / Manual Accent
COLOR_AMBER = QColor("#FFB800")          # High Load / Warning / Neutral
COLOR_RED = QColor("#FF4D6D")            # Critical / Brake Coral Red
COLOR_TEXT_PRIMARY = QColor("#FFFFFF")   # Pure White Readouts
COLOR_TEXT_SECONDARY = QColor("#9AE6B4") # Soft Mint / Sage Text
COLOR_TEXT_MUTED = QColor("#4E7566")     # Low-profile Muted Mints
COLOR_GAUGE_TRACK = QColor(12, 26, 20, 230)
COLOR_GAUGE_ACCENT = QColor(20, 44, 34, 240)

# Voltesse Race Display Cockpit Extensions
COLOR_EMERALD_CYAN = QColor("#00F5D4")             # Voltesse Emerald Cyan
COLOR_SHIFT_GREEN = QColor("#00F5A0")              # Neon Mint
COLOR_SHIFT_RED = QColor("#FF2A55")                # Vivid Race Red
COLOR_SHIFT_PURPLE = QColor("#A855F7")             # Rev Limit Purple
COLOR_SHIFT_PURPLE_BRIGHT = QColor("#D946EF")      # Shift Peak Purple
COLOR_SHIFT_FLASH = QColor("#FFFFFF")              # Specular Flash White
COLOR_SILVER_METALLIC = QColor("#E2E8F0")          # Display Silver

# Voltesse Black Mint OLED Beta Theme Palette
COLOR_OLED_BLACK = QColor("#000000")              # Pitch Black Void (OLED True Black)
COLOR_OLED_GLOW = QColor("#00E5FF")               # Electric Luminous Cyan
COLOR_OLED_MINT_GLOW = QColor("#00F5D4")          # Voltesse Emerald Mint
COLOR_OLED_RING = QColor(0, 229, 255, 180)        # Bezel Ring Neon Cyan
COLOR_OLED_GLASS = QColor(0, 229, 255, 60)        # Convex Glass Sheen Top
COLOR_OLED_NEEDLE = QColor("#FFFFFF")             # Specular White Needle
COLOR_OLED_NEEDLE_CYAN = QColor("#00F5D4")        # Glowing Needle Core
COLOR_OLED_BRAKE = QColor("#FF4D6D")              # Vivid Coral Red Brake / Alert
COLOR_OLED_AMBER = QColor("#FFB800")              # Warning Amber
COLOR_OLED_MUTED = QColor("#3E6558")              # Subtle Inactive Scale


# =====================================================================
# Voltesse Ambient Theme & Accent Palette Suite (v5.4.0)
# =====================================================================
@dataclass(frozen=True)
class AmbientPalette:
    key: str
    name: str
    primary: QColor
    highlight: QColor
    secondary: QColor
    dim: QColor
    border: QColor
    text_accent: QColor


PALETTES: dict[str, AmbientPalette] = {
    "mint": AmbientPalette(
        key="mint",
        name="CYBER-MINT",
        primary=QColor("#00F5A0"),
        highlight=QColor("#5CFFC7"),
        secondary=QColor("#00E5FF"),
        dim=QColor(0, 245, 160, 45),
        border=QColor(0, 245, 160, 80),
        text_accent=QColor("#5CFFC7"),
    ),
    "stealth": AmbientPalette(
        key="stealth",
        name="STEALTH-MONOCHROME",
        primary=QColor("#E2E8F0"),
        highlight=QColor("#FFFFFF"),
        secondary=QColor("#94A3B8"),
        dim=QColor(226, 232, 240, 45),
        border=QColor(226, 232, 240, 80),
        text_accent=QColor("#FFFFFF"),
    ),
    "amber": AmbientPalette(
        key="amber",
        name="SOLAR-AMBER",
        primary=QColor("#FFB800"),
        highlight=QColor("#FFD166"),
        secondary=QColor("#FF9F1C"),
        dim=QColor(255, 184, 0, 45),
        border=QColor(255, 184, 0, 80),
        text_accent=QColor("#FFD166"),
    ),
    "redline": AmbientPalette(
        key="redline",
        name="TRACK-REDLINE",
        primary=QColor("#FF3366"),
        highlight=QColor("#FF6B8B"),
        secondary=QColor("#FF9900"),
        dim=QColor(255, 51, 102, 45),
        border=QColor(255, 51, 102, 80),
        text_accent=QColor("#FF6B8B"),
    ),
    "synthwave": AmbientPalette(
        key="synthwave",
        name="NEON-SYNTHWAVE",
        primary=QColor("#D946EF"),
        highlight=QColor("#F472B6"),
        secondary=QColor("#06B6D4"),
        dim=QColor(217, 70, 239, 45),
        border=QColor(217, 70, 239, 80),
        text_accent=QColor("#F472B6"),
    ),
}

PALETTE_KEYS: list[str] = ["mint", "stealth", "amber", "redline", "synthwave"]


def get_palette(key: str | AmbientPalette) -> AmbientPalette:
    """Resolves an AmbientPalette instance from string key or returns palette unchanged."""
    if isinstance(key, AmbientPalette):
        return key
    norm = str(key).strip().lower()
    return PALETTES.get(norm, PALETTES["mint"])


class SpeedometerDialWidget(QWidget):
    """
    Sleek automotive digital instrument cluster with Full Black Mint OLED Theme.
    Features a 3-pod automotive binnacle layout with flowing luminous cowl brow,
    outer bezel glowing neon rings, convex glass reflection highlight, precision
    speedometer needle, large pure-white digital speed, dynamic ACCEL/BRAKE curved
    ribbon meter, tachometer (0-8 x1000 RPM) with vertical coolant temp (°F), and
    twin-needle battery SoC (E-F) and powertrain thermal (C-H) gauges.
    Auto-scales cleanly to any screen size and aspect ratio.
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
        self.motor_rpm = 0
        self.max_rpm = 8000
        self.throttle_pct = 0.0
        self.brake_pct = 0.0
        self.steering_angle = 0.0
        self.active_gear = "D1"
        self.transmission_mode = "AUTO"  # "AUTO" or "MANUAL"
        self.drive_mode = "DRIVE"
        # Aux telemetry for OLED binnacle display
        self.battery_soc = 88.0
        self.motor_temp_c = 72.0
        self.inverter_temp_c = 48.0
        self.trip_dist_mi = 9999.0
        self.battery_voltage = 398.0
        self.battery_power_kw = 42.0
        self.cluster_theme = "OLED"  # "OLED" or "CLASSIC"
        self.palette: AmbientPalette = PALETTES["mint"]
        self._palette_toast_name: str = "CYBER-MINT"
        self._palette_toast_alpha: float = 0.0
        self._palette_toast_start_time: float = 0.0
        self._palette_toast_timer: Optional[QTimer] = None
        self.is_sweeping = False
        self.sweep_progress = 0.0
        self._sweep_anim: Optional[QVariantAnimation] = None

        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 160)
        self.setMinimumWidth(0)

    def startup_needle_sweep(self) -> None:
        """Triggers a 1.2-second startup needle sweep sequence across all binnacle gauges."""
        if hasattr(self, "_sweep_anim") and self._sweep_anim is not None:
            self._sweep_anim.stop()
        self.is_sweeping = True
        self.sweep_progress = 0.0

        anim = QVariantAnimation(self)
        anim.setDuration(1200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def _on_value(val):
            self.sweep_progress = float(val)
            self.update()

        def _on_finish():
            self.is_sweeping = False
            self.sweep_progress = 1.0
            self.update()

        anim.valueChanged.connect(_on_value)
        anim.finished.connect(_on_finish)
        self._sweep_anim = anim
        anim.start()

    def finish_sweep(self) -> None:
        """Immediately finishes or aborts the sweep sequence to display live telemetry."""
        if getattr(self, "is_sweeping", False):
            if hasattr(self, "_sweep_anim") and self._sweep_anim is not None:
                self._sweep_anim.stop()
            self.is_sweeping = False
            self.sweep_progress = 1.0
            self.update()

    def set_units(self, unit: str = "KM/H", max_val: float = 180.0) -> None:
        self.unit = unit
        self.max_val = max_val
        self.update()

    def set_value(self, value: float, sub_val: str = "") -> None:
        self.current_val = max(self.min_val, min(self.max_val, value))
        if sub_val:
            self.sub_val = str(sub_val)
            try:
                clean_rpm = str(sub_val).replace(",", "").strip()
                self.motor_rpm = max(0, int(float(clean_rpm)))
            except (ValueError, TypeError):
                pass
        self.update()

    def set_motor_rpm(self, rpm: int) -> None:
        self.motor_rpm = max(0, int(rpm))
        self.sub_val = str(self.motor_rpm)
        self.update()

    def set_pedals_and_gear(
        self,
        throttle: float,
        brake: float,
        gear: str = "D1",
        mode: str = "DRIVE",
        steering_angle: float = 0.0,
        transmission_mode: str = "AUTO",
        motor_rpm: Optional[int] = None,
    ) -> None:
        self.throttle_pct = throttle
        self.brake_pct = brake
        self.active_gear = gear
        self.drive_mode = mode
        self.steering_angle = steering_angle
        self.transmission_mode = transmission_mode
        if motor_rpm is not None:
            self.motor_rpm = max(0, int(motor_rpm))
            self.sub_val = str(self.motor_rpm)
        self.update()

    def set_aux_telemetry(
        self,
        soc: float = 88.0,
        motor_temp_c: float = 72.0,
        inverter_temp_c: float = 48.0,
        trip_dist_mi: float = 9999.0,
        battery_voltage: float = 398.0,
        battery_power_kw: float = 42.0,
    ) -> None:
        """Sets auxiliary battery, thermal, and trip distance telemetry for OLED binnacle."""
        self.battery_soc = max(0.0, min(100.0, float(soc)))
        self.motor_temp_c = float(motor_temp_c)
        self.inverter_temp_c = float(inverter_temp_c)
        self.trip_dist_mi = max(0.0, float(trip_dist_mi))
        self.battery_voltage = float(battery_voltage)
        self.battery_power_kw = float(battery_power_kw)
        self.update()

    def set_cluster_theme(self, theme: str) -> None:
        """Switches cluster rendering theme ('OLED' or 'CLASSIC')."""
        self.cluster_theme = str(theme).upper()
        self.update()

    def set_palette(self, palette: AmbientPalette | str) -> None:
        """Sets the active ambient accent palette for the OLED cluster."""
        self.palette = get_palette(palette)
        self.update()

    def show_palette_toast(self, palette_name: str) -> None:
        """Triggers a 1.5-second centered glassmorphic notification overlay."""
        self._palette_toast_name = palette_name
        self._palette_toast_alpha = 1.0
        self._palette_toast_start_time = time.time()
        if not hasattr(self, "_palette_toast_timer") or self._palette_toast_timer is None:
            self._palette_toast_timer = QTimer(self)
            self._palette_toast_timer.setInterval(30)
            self._palette_toast_timer.timeout.connect(self._step_palette_toast)
        self._palette_toast_timer.start()
        self.update()

    def _step_palette_toast(self) -> None:
        now = time.time()
        elapsed = now - getattr(self, "_palette_toast_start_time", now)
        if elapsed < 0.8:
            self._palette_toast_alpha = 1.0
        elif elapsed < 1.5:
            # Smooth cubic fade out
            t = (elapsed - 0.8) / 0.7
            self._palette_toast_alpha = max(0.0, 1.0 - (t * t))
        else:
            self._palette_toast_alpha = 0.0
            if hasattr(self, "_palette_toast_timer") and self._palette_toast_timer is not None:
                self._palette_toast_timer.stop()
        self.update()

    @property
    def _toast_active(self) -> bool:
        return getattr(self, "_palette_toast_alpha", 0.0) > 0.0

    @property
    def _toast_text(self) -> str:
        return getattr(self, "_palette_toast_name", "")

    @property
    def _toast_alpha(self) -> float:
        return getattr(self, "_palette_toast_alpha", 0.0)

    def _draw_palette_toast(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        alpha = getattr(self, "_palette_toast_alpha", 0.0)
        if alpha <= 0.01:
            return

        name = getattr(self, "_palette_toast_name", self.palette.name)
        pill_w = max(190.0, r * 1.15)
        pill_h = max(36.0, r * 0.24)
        pill_x = cx - (pill_w / 2.0)
        pill_y = cy - (pill_h / 2.0)
        pill_rect = QRectF(pill_x, pill_y, pill_w, pill_h)

        bg_col = QColor(4, 12, 10, int(230 * alpha))
        border_col = QColor(self.palette.highlight.red(), self.palette.highlight.green(), self.palette.highlight.blue(), int(220 * alpha))

        painter.save()
        painter.setBrush(QBrush(bg_col))
        painter.setPen(QPen(border_col, 1.5))
        painter.drawRoundedRect(pill_rect, pill_h / 2.0, pill_h / 2.0)

        # Subtle ambient halo glow
        glow_pen_col = QColor(self.palette.primary.red(), self.palette.primary.green(), self.palette.primary.blue(), int(70 * alpha))
        painter.setPen(QPen(glow_pen_col, 4.0))
        painter.drawRoundedRect(pill_rect.adjusted(-2, -2, 2, 2), (pill_h + 4) / 2.0, (pill_h + 4) / 2.0)

        # Centered text: 🎨 PALETTE: [NAME]
        text_col = QColor(self.palette.highlight.red(), self.palette.highlight.green(), self.palette.highlight.blue(), int(255 * alpha))
        painter.setPen(text_col)
        font = QFont("Segoe UI", max(8, min(13, int(r * 0.082))), QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        painter.setFont(font)
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, f"🎨 {name}")
        painter.restore()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        try:
            w = self.width()
            h = self.height()
            if getattr(self, "cluster_theme", "OLED") == "OLED":
                self._paint_oled_theme(painter, w, h)
            else:
                self._paint_classic_theme(painter, w, h)
        finally:
            painter.end()

    def _paint_oled_theme(self, painter: QPainter, w: int, h: int) -> None:
        """Renders Full Black Mint OLED 3-Pod Instrument Binnacle matching reference photo."""
        # 1. Pitch Black OLED Background (True Black #000000, zero grey cards)
        painter.fillRect(0, 0, w, h, COLOR_OLED_BLACK)

        is_wide = (w >= 540) and (w / max(1.0, float(h)) >= 1.20)

        if not is_wide:
            self._draw_center_pod(painter, w / 2.0, h / 2.0, min(w, h) * 0.44)
            if getattr(self, "_palette_toast_alpha", 0.0) > 0.01:
                self._draw_palette_toast(painter, w / 2.0, h / 2.0, min(w, h) * 0.44)
            return

        # 2. Geometry for 3-Pod Instrument Binnacle
        center_r = min(h * 0.45, (w - 30.0) / 4.45)
        side_r = center_r * 0.77

        cx = w / 2.0
        cy_center = h * 0.49
        dist_x = center_r * 0.91 + side_r * 0.89
        cx_left = cx - dist_x
        cx_right = cx + dist_x
        cy_left = cy_center + (center_r - side_r) * 0.24
        cy_right = cy_left

        # 3. Draw Side Pods First (So center pod naturally sits in front)
        self._draw_left_pod(painter, cx_left, cy_left, side_r)
        self._draw_right_pod(painter, cx_right, cy_right, side_r)

        # 4. Draw Center Pod (Prominent centerpiece)
        self._draw_center_pod(painter, cx, cy_center, center_r)

        # 5. Draw Top Flowing Cowl Luminous Brow across all 3 pods
        self._draw_flowing_cowl(painter, cx_left, cy_left, side_r, cx, cy_center, center_r, cx_right, cy_right, side_r)

        # 6. Centered Glassmorphic Palette Overlay Notification (if active)
        if getattr(self, "_palette_toast_alpha", 0.0) > 0.01:
            self._draw_palette_toast(painter, cx, cy_center, center_r)

    def _draw_flowing_cowl(
        self, painter: QPainter, cx_l: float, cy_l: float, r_l: float,
        cx_c: float, cy_c: float, r_c: float, cx_r: float, cy_r: float, r_r: float,
    ) -> None:
        """Draws the ethereal glowing cybernetic brow line arching over the cluster."""
        path = QPainterPath()
        p_start_x = cx_l - r_l * 1.02
        p_start_y = cy_l + r_l * 0.15
        path.moveTo(p_start_x, p_start_y)

        # Arch over left pod
        cp1_x = cx_l - r_l * 0.70
        cp1_y = cy_l - r_l * 1.05
        cp2_x = cx_l + r_l * 0.20
        cp2_y = cy_l - r_l * 1.08
        mid_dip_left_x = (cx_l + cx_c) / 2.0 - (r_c * 0.15)
        mid_dip_left_y = cy_c - r_c * 0.75
        path.cubicTo(cp1_x, cp1_y, cp2_x, cp2_y, mid_dip_left_x, mid_dip_left_y)

        # Rise over center dome
        cp_c1_x = cx_c - r_c * 0.55
        cp_c1_y = cy_c - r_c * 1.15
        cp_c2_x = cx_c + r_c * 0.55
        cp_c2_y = cy_c - r_c * 1.15
        mid_dip_right_x = (cx_c + cx_r) / 2.0 + (r_c * 0.15)
        mid_dip_right_y = cy_c - r_c * 0.75
        path.cubicTo(cp_c1_x, cp_c1_y, cp_c2_x, cp_c2_y, mid_dip_right_x, mid_dip_right_y)

        # Arch over right pod
        cp_r1_x = cx_r - r_r * 0.20
        cp_r1_y = cy_r - r_r * 1.08
        cp_r2_x = cx_r + r_r * 0.70
        cp_r2_y = cy_r - r_r * 1.05
        p_end_x = cx_r + r_r * 1.02
        p_end_y = cy_r + r_r * 0.15
        path.cubicTo(cp_r1_x, cp_r1_y, cp_r2_x, cp_r2_y, p_end_x, p_end_y)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        cowl_dim = QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 35)
        painter.setPen(QPen(cowl_dim, 7.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

        cowl_pri = QColor(self.palette.primary.red(), self.palette.primary.green(), self.palette.primary.blue(), 110)
        painter.setPen(QPen(cowl_pri, 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

        cowl_high = QColor(self.palette.highlight.red(), self.palette.highlight.green(), self.palette.highlight.blue(), 245)
        painter.setPen(QPen(cowl_high, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

    def _draw_left_pod(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        """Left Pod: Motor Tachometer (0-8 x1000 RPM) + Refined Vertical Temperature Sub-Gauge (°F)."""
        grad = QRadialGradient(QPointF(cx, cy), r)
        grad.setColorAt(0.0, QColor(4, 12, 9, 220))
        grad.setColorAt(0.85, QColor(2, 6, 4, 240))
        grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 100), 1.2))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        r_track = r * 0.88
        painter.setBrush(Qt.BrushStyle.NoBrush)

        start_angle_deg = 225.0
        total_span_deg = -170.0

        painter.setPen(QPen(QColor(10, 28, 20, 220), max(2.0, r * 0.025)))
        painter.drawArc(QRectF(cx - r_track, cy - r_track, r_track * 2, r_track * 2), int(start_angle_deg * 16), int(total_span_deg * 16))

        # Redline Sector Arc (between 7 and 8)
        redline_start_ang = start_angle_deg + (total_span_deg * (7.0 / 8.0))
        redline_span = total_span_deg * (1.0 / 8.0)
        painter.setPen(QPen(QColor(255, 77, 109, 140), max(2.5, r * 0.035)))
        painter.drawArc(QRectF(cx - r_track, cy - r_track, r_track * 2, r_track * 2), int(redline_start_ang * 16), int(redline_span * 16))

        font_num = QFont("Segoe UI", max(7, min(14, int(r * 0.115))), QFont.Weight.Bold)

        for i in range(9):
            fraction = i / 8.0
            ang = start_angle_deg + (total_span_deg * fraction)
            rad = -math.radians(ang)

            is_redline = (i >= 7)
            tick_col = COLOR_RED if is_redline else COLOR_TEXT_PRIMARY
            tick_len = r * 0.09
            r_outer = r_track - 1.0
            r_inner = r_outer - tick_len

            x1 = cx + math.cos(rad) * r_outer
            y1 = cy + math.sin(rad) * r_outer
            x2 = cx + math.cos(rad) * r_inner
            y2 = cy + math.sin(rad) * r_inner

            painter.setPen(QPen(tick_col, max(1.2, r * 0.016)))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Major Number
            r_num = r_inner - (r * 0.11)
            nx = cx + math.cos(rad) * r_num
            ny = cy + math.sin(rad) * r_num
            nw = r * 0.28
            nh = r * 0.18
            painter.setFont(font_num)
            painter.setPen(tick_col)
            painter.drawText(QRectF(nx - (nw / 2.0), ny - (nh / 2.0), nw, nh), Qt.AlignmentFlag.AlignCenter, str(i))

            # Minor half-tick
            if i < 8:
                half_ang = start_angle_deg + (total_span_deg * (fraction + (0.5 / 8.0)))
                half_rad = -math.radians(half_ang)
                hx1 = cx + math.cos(half_rad) * r_outer
                hy1 = cy + math.sin(half_rad) * r_outer
                hx2 = cx + math.cos(half_rad) * (r_outer - tick_len * 0.55)
                hy2 = cy + math.sin(half_rad) * (r_outer - tick_len * 0.55)
                painter.setPen(QPen(COLOR_RED if i >= 6 else QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 120), 1.0))
                painter.drawLine(QPointF(hx1, hy1), QPointF(hx2, hy2))

        # RPM x1000 label
        lbl_rect = QRectF(cx - r * 0.26, cy - r * 0.50, r * 0.40, r * 0.24)
        painter.setFont(QFont("Segoe UI", max(6, min(10, int(r * 0.075))), QFont.Weight.Bold))
        painter.setPen(self.palette.primary)
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, "RPM\nx1000")

        # Luminous Tachometer Needle
        effective_rpm = self.motor_rpm
        if effective_rpm <= 0 and self.current_val > 0.5:
            effective_rpm = int(min(8000.0, (self.current_val / max(1.0, self.max_val)) * 7200.0))
        live_rpm_ratio = min(1.0, max(0.0, effective_rpm / 8000.0))
        if getattr(self, "is_sweeping", False):
            p = getattr(self, "sweep_progress", 0.0)
            if p < 0.5:
                rpm_ratio = p * 2.0
            else:
                rpm_ratio = 1.0 - (1.0 - live_rpm_ratio) * ((p - 0.5) * 2.0)
        else:
            rpm_ratio = live_rpm_ratio
        needle_ang = start_angle_deg + (total_span_deg * rpm_ratio)
        needle_rad = -math.radians(needle_ang)

        tip_x = cx + math.cos(needle_rad) * (r_track * 0.88)
        tip_y = cy + math.sin(needle_rad) * (r_track * 0.88)

        p_rad_left = needle_rad + math.pi / 2.0
        p_rad_right = needle_rad - math.pi / 2.0
        base_w = r * 0.045
        b1_x = cx + math.cos(p_rad_left) * base_w
        b1_y = cy + math.sin(p_rad_left) * base_w
        b2_x = cx + math.cos(p_rad_right) * base_w
        b2_y = cy + math.sin(p_rad_right) * base_w

        poly = QPolygonF([QPointF(b1_x, b1_y), QPointF(tip_x, tip_y), QPointF(b2_x, b2_y)])
        painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
        painter.setPen(QPen(QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 180), 0.8))
        painter.drawPolygon(poly)

        # Center Hub Cap
        hub_r = r * 0.12
        painter.setBrush(QBrush(QColor(6, 16, 12, 245)))
        painter.setPen(QPen(self.palette.secondary, 1.5))
        painter.drawEllipse(QPointF(cx, cy), hub_r, hub_r)

        # Refined Vertical Temperature Sub-Gauge on Right Flank of Left Pod (Zero Overlap)
        sub_x = cx + r * 0.50
        bar_top_y = cy - r * 0.18
        bar_bot_y = cy + r * 0.48
        bar_h = bar_bot_y - bar_top_y

        painter.setFont(QFont("Segoe UI", max(5, min(9, int(r * 0.068))), QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(sub_x - r * 0.24, bar_top_y - 8, r * 0.22, 12), Qt.AlignmentFlag.AlignRight, "320")
        painter.drawText(QRectF(sub_x - r * 0.24, cy + r * 0.12 - 6, r * 0.22, 12), Qt.AlignmentFlag.AlignRight, "200")
        painter.drawText(QRectF(sub_x - r * 0.24, bar_bot_y - 8, r * 0.22, 12), Qt.AlignmentFlag.AlignRight, "100")

        # Vector Thermometer Icon + °F Label
        motor_temp_f = self.motor_temp_c * 9.0 / 5.0 + 32.0
        pip_col = COLOR_RED if motor_temp_f >= 220 else (COLOR_AMBER if motor_temp_f >= 180 else self.palette.primary)

        thermo_stem_x = sub_x - r * 0.14
        thermo_top_y = cy + r * 0.24
        painter.setBrush(QBrush(pip_col))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(thermo_stem_x - 1.2, thermo_top_y, 2.4, 7.0), 1.0, 1.0)
        painter.drawEllipse(QPointF(thermo_stem_x, thermo_top_y + 8.5), 2.5, 2.5)

        painter.setFont(QFont("Segoe UI", max(6, min(9, int(r * 0.075))), QFont.Weight.Bold))
        painter.setPen(pip_col)
        painter.drawText(QRectF(sub_x - r * 0.10, cy + r * 0.23, r * 0.14, 12), Qt.AlignmentFlag.AlignLeft, "°F")

        # Vertical Track & Tick Marks
        painter.setPen(QPen(QColor(10, 28, 20, 220), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(sub_x, bar_top_y), QPointF(sub_x, bar_bot_y))

        # Horizontal Ticks
        painter.setPen(QPen(QColor(18, 50, 38, 200), 1.0))
        painter.drawLine(QPointF(sub_x, bar_top_y), QPointF(sub_x + 4, bar_top_y))
        painter.drawLine(QPointF(sub_x, cy + r * 0.12), QPointF(sub_x + 3, cy + r * 0.12))
        painter.drawLine(QPointF(sub_x, bar_bot_y), QPointF(sub_x + 4, bar_bot_y))

        # Dynamic Fluid Level Line & Floating Pip
        t_frac = min(1.0, max(0.0, (motor_temp_f - 100.0) / 220.0))
        cur_temp_y = bar_bot_y - (bar_h * t_frac)
        painter.setPen(QPen(pip_col, 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(sub_x, bar_bot_y), QPointF(sub_x, cur_temp_y))

        painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
        painter.setPen(QPen(pip_col, 1.0))
        painter.drawRect(QRectF(sub_x - 1, cur_temp_y - 1.5, r * 0.06, 3.0))


    def _draw_right_pod(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        """Right Pod: Summarized Battery Information Widget (SoC % Arc, Range, Pack Metrics)."""
        grad = QRadialGradient(QPointF(cx, cy), r)
        grad.setColorAt(0.0, QColor(4, 12, 9, 220))
        grad.setColorAt(0.85, QColor(2, 6, 4, 240))
        grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 100), 1.2))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        r_track = r * 0.86
        track_rect = QRectF(cx - r_track, cy - r_track, r_track * 2, r_track * 2)

        start_angle_deg = 210.0
        total_span_deg = -240.0

        # 1. Background Gauge Track
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(10, 28, 20, 220), max(3.5, r * 0.038), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(track_rect, int(start_angle_deg * 16), int(total_span_deg * 16))

        # 2. Compute Active SoC Ratio (with startup sweep support)
        live_soc_ratio = min(1.0, max(0.0, self.battery_soc / 100.0))
        if getattr(self, "is_sweeping", False):
            p = getattr(self, "sweep_progress", 0.0)
            if p < 0.5:
                soc_ratio = p * 2.0
            else:
                soc_ratio = 1.0 - (1.0 - live_soc_ratio) * ((p - 0.5) * 2.0)
        else:
            soc_ratio = live_soc_ratio

        if soc_ratio > 0.20:
            soc_col = self.palette.primary
        elif soc_ratio > 0.10:
            soc_col = COLOR_AMBER
        else:
            soc_col = COLOR_RED

        # 3. Active SoC Glowing Arc
        active_span_deg = total_span_deg * soc_ratio
        if soc_ratio > 0.005:
            pen_active = QPen(soc_col, max(3.8, r * 0.040), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_active)
            painter.drawArc(track_rect, int(start_angle_deg * 16), int(active_span_deg * 16))

            # Beacon pip at active tip
            tip_ang = start_angle_deg + active_span_deg
            tip_rad = -math.radians(tip_ang)
            tip_x = cx + math.cos(tip_rad) * r_track
            tip_y = cy + math.sin(tip_rad) * r_track
            painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
            painter.setPen(QPen(soc_col, 1.6))
            painter.drawEllipse(QPointF(tip_x, tip_y), max(2.5, r * 0.024), max(2.5, r * 0.024))

        # 4. Graduation Ticks & E / F Markers
        font_ef = QFont("Segoe UI", max(7, min(12, int(r * 0.095))), QFont.Weight.Bold)
        painter.setFont(font_ef)

        # 'E' at 210 deg (Bottom-Left)
        e_rad = -math.radians(start_angle_deg)
        e_x = cx + math.cos(e_rad) * (r_track * 0.74)
        e_y = cy + math.sin(e_rad) * (r_track * 0.74)
        painter.setPen(COLOR_RED if soc_ratio <= 0.15 else COLOR_TEXT_MUTED)
        painter.drawText(QRectF(e_x - 12, e_y - 10, 24, 20), Qt.AlignmentFlag.AlignCenter, "E")

        # 'F' at -30 deg (Bottom-Right)
        f_rad = -math.radians(start_angle_deg + total_span_deg)
        f_x = cx + math.cos(f_rad) * (r_track * 0.74)
        f_y = cy + math.sin(f_rad) * (r_track * 0.74)
        painter.setPen(self.palette.primary if soc_ratio >= 0.85 else COLOR_TEXT_MUTED)
        painter.drawText(QRectF(f_x - 12, f_y - 10, 24, 20), Qt.AlignmentFlag.AlignCenter, "F")

        # Graduation ticks (25%, 50%, 75%)
        for frac in (0.25, 0.50, 0.75):
            tick_ang = start_angle_deg + (total_span_deg * frac)
            tick_rad = -math.radians(tick_ang)
            tx1 = cx + math.cos(tick_rad) * (r_track - 2.0)
            ty1 = cy + math.sin(tick_rad) * (r_track - 2.0)
            tx2 = cx + math.cos(tick_rad) * (r_track - r * 0.07)
            ty2 = cy + math.sin(tick_rad) * (r_track - r * 0.07)
            is_passed = (frac <= soc_ratio)
            painter.setPen(QPen(soc_col if is_passed else QColor(10, 32, 22, 220), 1.2))
            painter.drawLine(QPointF(tx1, ty1), QPointF(tx2, ty2))

        # 5. Top Center Vector EV Battery Icon
        icon_w = max(18.0, r * 0.16)
        icon_h = icon_w * 0.50
        icon_x = cx - (icon_w / 2.0)
        icon_y = cy - r * 0.56
        painter.setPen(QPen(soc_col, 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(icon_x, icon_y, icon_w, icon_h), 1.5, 1.5)
        # Terminal nub
        painter.fillRect(QRectF(icon_x + icon_w, icon_y + (icon_h * 0.25), 2.0, icon_h * 0.50), soc_col)
        # Inner fill level
        fill_w = max(0.0, (icon_w - 3.0) * soc_ratio)
        if fill_w > 0:
            painter.fillRect(QRectF(icon_x + 1.5, icon_y + 1.5, fill_w, icon_h - 3.0), soc_col)

        # 6. Central Large Digital SoC Numerals & Tag
        disp_soc = int(round(soc_ratio * 100.0))
        font_soc = QFont("Segoe UI", max(22, min(50, int(r * 0.32))), QFont.Weight.Bold)
        painter.setFont(font_soc)
        painter.setPen(COLOR_TEXT_PRIMARY)
        soc_rect = QRectF(cx - r * 0.50, cy - r * 0.28, r * 1.0, r * 0.34)
        painter.drawText(soc_rect, Qt.AlignmentFlag.AlignCenter, f"{disp_soc}%")

        font_sub = QFont("Segoe UI", max(6, min(10, int(r * 0.068))), QFont.Weight.Bold)
        font_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        painter.setFont(font_sub)
        painter.setPen(soc_col)
        sub_tag_rect = QRectF(cx - r * 0.40, cy + r * 0.04, r * 0.80, r * 0.12)
        painter.drawText(sub_tag_rect, Qt.AlignmentFlag.AlignCenter, "BATTERY")

        # 7. Prominent Estimated Range Pill Badge
        range_mi = int(round(soc_ratio * 261.0))
        badge_w = r * 0.72
        badge_h = max(16.0, r * 0.18)
        badge_x = cx - (badge_w / 2.0)
        badge_y = cy + r * 0.18
        badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)
        painter.setBrush(QBrush(self.palette.dim))
        painter.setPen(QPen(self.palette.border, 1.0))
        painter.drawRoundedRect(badge_rect, badge_h / 2.0, badge_h / 2.0)

        # Vector navigation marker / lightning icon
        pin_x = badge_x + (badge_h * 0.52)
        pin_y = badge_y + (badge_h * 0.50)
        pin_poly = QPolygonF([
            QPointF(pin_x - 3.5, pin_y - 3.5),
            QPointF(pin_x + 3.5, pin_y - 3.5),
            QPointF(pin_x, pin_y + 4.0),
        ])
        painter.setBrush(QBrush(self.palette.secondary))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(pin_poly)

        font_range = QFont("Segoe UI", max(8, min(13, int(r * 0.088))), QFont.Weight.Bold)
        painter.setFont(font_range)
        painter.setPen(self.palette.highlight)
        range_text_rect = QRectF(pin_x + 4.0, badge_y, badge_w - (pin_x - badge_x) - 4.0, badge_h)
        painter.drawText(range_text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{range_mi} mi")

        # 8. Live Electrical Pack Telemetry (Voltage & Power)
        volt_val = int(round(getattr(self, "battery_voltage", 398.0)))
        power_val = getattr(self, "battery_power_kw", 42.0)
        if power_val < -0.5:
            pwr_str = f"{power_val:.0f}kW"
            pwr_col = self.palette.primary
        elif power_val > 0.5:
            pwr_str = f"+{power_val:.0f}kW"
            pwr_col = self.palette.secondary
        else:
            pwr_str = "0kW"
            pwr_col = COLOR_TEXT_MUTED

        elec_str = f"{volt_val}V  •  {pwr_str}"
        font_elec = QFont("Consolas", max(7, min(11, int(r * 0.075))), QFont.Weight.Bold)
        painter.setFont(font_elec)
        painter.setPen(self.palette.secondary)
        elec_rect = QRectF(cx - r * 0.50, cy + r * 0.52, r * 1.0, r * 0.16)
        painter.drawText(elec_rect, Qt.AlignmentFlag.AlignCenter, elec_str)

    def _draw_center_pod(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        """Center Pod: Speedometer with Glass Reflection, Speed Needle, Digital Readout, Ribbon Meter, Gear, Odo."""
        # 1. Bezel Ring Halo Glow
        glow_alpha = 50
        if getattr(self, "is_sweeping", False):
            p = getattr(self, "sweep_progress", 0.0)
            pulse = math.sin(p * math.pi)
            glow_alpha = int(50 + 110 * pulse)
        glow_grad = QRadialGradient(QPointF(cx, cy), r * 1.12)
        glow_grad.setColorAt(0.82, QColor(0, 0, 0, 0))
        glow_grad.setColorAt(0.94, QColor(self.palette.primary.red(), self.palette.primary.green(), self.palette.primary.blue(), glow_alpha))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), r * 1.12, r * 1.12)

        # Dark Dial Face
        face_grad = QRadialGradient(QPointF(cx, cy), r)
        face_grad.setColorAt(0.0, QColor(5, 14, 11, 235))
        face_grad.setColorAt(0.85, QColor(2, 6, 4, 245))
        face_grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.setBrush(QBrush(face_grad))
        painter.setPen(QPen(QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 190), 2.2))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Concentric Recessed Track Ring
        r_track = r * 0.93
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(12, 28, 22, 220), max(3.0, r * 0.024)))
        start_angle_deg = 225.0
        total_span_deg = -270.0
        painter.drawArc(QRectF(cx - r_track, cy - r_track, r_track * 2, r_track * 2), int(start_angle_deg * 16), int(total_span_deg * 16))

        # 2. UPPER CONVEX GLASS REFLECTION HIGHLIGHT
        painter.save()
        clip_path = QPainterPath()
        clip_path.addEllipse(QPointF(cx, cy), r * 0.97, r * 0.97)
        painter.setClipPath(clip_path)

        glass_grad = QRadialGradient(QPointF(cx, cy - r * 0.65), r * 0.85)
        glass_grad.setColorAt(0.0, QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 80))
        glass_grad.setColorAt(0.40, QColor(self.palette.highlight.red(), self.palette.highlight.green(), self.palette.highlight.blue(), 45))
        glass_grad.setColorAt(0.75, QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 12))
        glass_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(glass_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy - r * 0.45), r * 0.92, r * 0.55)
        painter.restore()

        # 3. Speed Graduation Ticks and Numbers
        major_nums = [0, 20, 40, 60, 80, 100, 120, 140, 160, 180]
        dial_max = 180.0
        num_ticks = len(major_nums)
        font_tick = QFont("Segoe UI", max(7, min(14, int(r * 0.082))), QFont.Weight.Bold)

        for idx, val in enumerate(major_nums):
            fraction = val / dial_max
            ang = start_angle_deg + (total_span_deg * fraction)
            rad = -math.radians(ang)

            tick_len = r * 0.085
            r_outer = r_track - 1.0
            r_inner = r_outer - tick_len

            x1 = cx + math.cos(rad) * r_outer
            y1 = cy + math.sin(rad) * r_outer
            x2 = cx + math.cos(rad) * r_inner
            y2 = cy + math.sin(rad) * r_inner

            painter.setPen(QPen(COLOR_TEXT_PRIMARY, max(1.5, r * 0.016)))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            r_num = r_inner - (r * 0.10)
            nx = cx + math.cos(rad) * r_num
            ny = cy + math.sin(rad) * r_num
            nw = r * 0.28
            nh = r * 0.16
            painter.setFont(font_tick)
            painter.setPen(COLOR_TEXT_PRIMARY)
            painter.drawText(QRectF(nx - (nw / 2.0), ny - (nh / 2.0), nw, nh), Qt.AlignmentFlag.AlignCenter, str(val))

            if idx < num_ticks - 1:
                half_ang = start_angle_deg + (total_span_deg * ((val + 10.0) / dial_max))
                half_rad = -math.radians(half_ang)
                hx1 = cx + math.cos(half_rad) * r_outer
                hy1 = cy + math.sin(half_rad) * r_outer
                hx2 = cx + math.cos(half_rad) * (r_outer - tick_len * 0.55)
                hy2 = cy + math.sin(half_rad) * (r_outer - tick_len * 0.55)
                painter.setPen(QPen(QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 130), 1.0))
                painter.drawLine(QPointF(hx1, hy1), QPointF(hx2, hy2))

        # 4. Luminous Speed Needle (Pointing to current speed)
        live_spd_fraction = min(1.0, max(0.0, self.current_val / dial_max))
        if getattr(self, "is_sweeping", False):
            p = getattr(self, "sweep_progress", 0.0)
            if p < 0.5:
                spd_fraction = p * 2.0
            else:
                spd_fraction = 1.0 - (1.0 - live_spd_fraction) * ((p - 0.5) * 2.0)
        else:
            spd_fraction = live_spd_fraction
        needle_ang = start_angle_deg + (total_span_deg * spd_fraction)
        needle_rad = -math.radians(needle_ang)

        tip_x = cx + math.cos(needle_rad) * (r_track * 0.88)
        tip_y = cy + math.sin(needle_rad) * (r_track * 0.88)

        base_r = r * 0.26
        base_x = cx + math.cos(needle_rad) * base_r
        base_y = cy + math.sin(needle_rad) * base_r

        p_rad_left = needle_rad + math.pi / 2.0
        p_rad_right = needle_rad - math.pi / 2.0
        base_w = r * 0.032
        b1_x = base_x + math.cos(p_rad_left) * base_w
        b1_y = base_y + math.sin(p_rad_left) * base_w
        b2_x = base_x + math.cos(p_rad_right) * base_w
        b2_y = base_y + math.sin(p_rad_right) * base_w

        poly = QPolygonF([QPointF(b1_x, b1_y), QPointF(tip_x, tip_y), QPointF(b2_x, b2_y)])
        painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
        painter.setPen(QPen(QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 200), 0.8))
        painter.drawPolygon(poly)

        # 5. Central Digital Speed Numerals & Vector Chevrons
        chv_up_y = cy - r * 0.32
        chv_w = max(5.0, r * 0.045)
        chv_h = max(3.5, r * 0.032)
        chv_up = QPolygonF([
            QPointF(cx, chv_up_y - chv_h),
            QPointF(cx - chv_w, chv_up_y + chv_h),
            QPointF(cx + chv_w, chv_up_y + chv_h),
        ])
        painter.setBrush(QBrush(self.palette.primary))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(chv_up)

        if getattr(self, "is_sweeping", False):
            spd_val = int(round(spd_fraction * dial_max))
        else:
            spd_val = int(round(self.current_val))
        font_spd = QFont("Segoe UI", max(26, min(68, int(r * 0.34))), QFont.Weight.Bold)
        painter.setFont(font_spd)
        painter.setPen(COLOR_TEXT_PRIMARY)
        spd_rect = QRectF(cx - r * 0.45, cy - r * 0.20, r * 0.90, r * 0.38)
        painter.drawText(spd_rect, Qt.AlignmentFlag.AlignCenter, str(spd_val))

        font_unit = QFont("Segoe UI", max(8, min(13, int(r * 0.070))), QFont.Weight.Bold)
        painter.setFont(font_unit)
        painter.setPen(self.palette.primary)
        unit_rect = QRectF(cx - r * 0.30, cy + r * 0.16, r * 0.60, r * 0.14)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, self.unit)

        chv_dn_y = cy + r * 0.33
        chv_dn = QPolygonF([
            QPointF(cx, chv_dn_y + chv_h),
            QPointF(cx - chv_w, chv_dn_y - chv_h),
            QPointF(cx + chv_w, chv_dn_y - chv_h),
        ])
        painter.setBrush(QBrush(self.palette.primary))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(chv_dn)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 70), 1.0))
        painter.drawEllipse(QPointF(cx, cy), base_r, base_r)

        # 7. Curved Vertical Ribbon Meter on Right Flank (ACCEL / BRAKE)
        ribbon_r = r * 1.07
        ribbon_rect = QRectF(cx - ribbon_r, cy - ribbon_r, ribbon_r * 2, ribbon_r * 2)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(10, 28, 20, 220), max(3.5, r * 0.026), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(ribbon_rect, int(32.0 * 16), int(-64.0 * 16))

        m_x1 = cx + ribbon_r - (r * 0.035)
        m_x2 = cx + ribbon_r + (r * 0.035)
        painter.setPen(QPen(COLOR_TEXT_PRIMARY, 1.5))
        painter.drawLine(QPointF(m_x1, cy), QPointF(m_x2, cy))

        a_rad = -math.radians(38.0)
        a_x = cx + math.cos(a_rad) * (ribbon_r * 1.02)
        a_y = cy + math.sin(a_rad) * (ribbon_r * 1.02)
        painter.setFont(QFont("Segoe UI", max(6, min(10, int(r * 0.065))), QFont.Weight.Bold))
        painter.setPen(self.palette.primary)
        painter.drawText(QRectF(a_x - 10, a_y - 12, 45, 14), Qt.AlignmentFlag.AlignLeft, "ACCEL")

        b_rad = -math.radians(-38.0)
        b_x = cx + math.cos(b_rad) * (ribbon_r * 1.02)
        b_y = cy + math.sin(b_rad) * (ribbon_r * 1.02)
        painter.setFont(QFont("Segoe UI", max(6, min(10, int(r * 0.065))), QFont.Weight.Bold))
        painter.setPen(COLOR_RED)
        painter.drawText(QRectF(b_x - 10, b_y - 2, 45, 14), Qt.AlignmentFlag.AlignLeft, "BRAKE")

        if self.throttle_pct > 0.5:
            thr_span = 30.0 * (self.throttle_pct / 100.0)
            painter.setPen(QPen(self.palette.primary, max(3.5, r * 0.026), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(ribbon_rect, int(0 * 16), int(thr_span * 16))

            pip_rad = -math.radians(thr_span)
            px = cx + math.cos(pip_rad) * ribbon_r
            py = cy + math.sin(pip_rad) * ribbon_r
            painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px, py), 2.5, 2.5)
        elif self.brake_pct > 0.5:
            brk_span = -30.0 * (self.brake_pct / 100.0)
            painter.setPen(QPen(COLOR_RED, max(3.5, r * 0.026), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(ribbon_rect, int(0 * 16), int(brk_span * 16))

            pip_rad = -math.radians(brk_span)
            px = cx + math.cos(pip_rad) * ribbon_r
            py = cy + math.sin(pip_rad) * ribbon_r
            painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px, py), 2.5, 2.5)

        # 8. Bottom Center Readouts (Gear, Drive Mode, Odometer)
        gear_y = cy + r * 0.82
        painter.setFont(QFont("Segoe UI", max(8, min(14, int(r * 0.090))), QFont.Weight.Bold))
        painter.setPen(self.palette.secondary)
        painter.drawText(QRectF(cx - r * 0.40, gear_y, r * 0.35, 18), Qt.AlignmentFlag.AlignRight, self.active_gear)

        mode_char = self.drive_mode[0] if self.drive_mode else "D"
        painter.setPen(self.palette.primary)
        painter.drawText(QRectF(cx - r * 0.02, gear_y, r * 0.20, 18), Qt.AlignmentFlag.AlignLeft, mode_char)

        odo_str = f"{int(round(self.trip_dist_mi)):06d} mi"
        painter.setFont(QFont("Segoe UI", max(8, min(13, int(r * 0.076))), QFont.Weight.Bold))
        painter.setPen(self.palette.highlight)
        painter.drawText(QRectF(cx + r * 0.38, gear_y, r * 0.60, 18), Qt.AlignmentFlag.AlignLeft, odo_str)

    def _paint_classic_theme(self, painter: QPainter, w: int, h: int) -> None:
        """Renders Classic Dial Theme (shift LED light strip removed)."""
        side = min(w, h)
        cx = w / 2.0
        cy = h / 2.0

        effective_rpm = self.motor_rpm
        if effective_rpm <= 0 and self.current_val > 0.5:
            effective_rpm = int(min(8000.0, (self.current_val / max(1.0, self.max_val)) * 7200.0))
        rpm_ratio = min(1.0, max(0.0, effective_rpm / float(max(1000, self.max_rpm))))

        padding = max(14.0, side * 0.065)
        outer_r = (side / 2.0) - padding
        track_r = outer_r - (side * 0.025)
        track_w = max(4.0, min(12.0, side * 0.026))

        start_angle_deg = 225.0
        total_span_deg = -270.0

        # 1. Card Container: Obsidian Carbon-Matrix Background
        card_rect = QRectF(4, 4, w - 8, h - 8)
        grad_card = QLinearGradient(0, 4, 0, h - 4)
        grad_card.setColorAt(0.0, QColor(9, 20, 16, 245))
        grad_card.setColorAt(0.5, QColor(6, 14, 11, 240))
        grad_card.setColorAt(1.0, QColor(4, 9, 7, 250))
        painter.setBrush(QBrush(grad_card))
        painter.setPen(QPen(QColor(0, 245, 160, 55), 1))
        painter.drawRoundedRect(card_rect, 10, 10)

        # Subtle motorsport carbon weave pattern
        painter.setPen(QPen(QColor(0, 245, 160, 6), 1))
        step_diag = max(8, int(side * 0.04))
        for diag_x in range(int(card_rect.left()), int(card_rect.right() + card_rect.height()), step_diag):
            p1 = QPointF(diag_x, card_rect.top())
            p2 = QPointF(diag_x - card_rect.height(), card_rect.bottom())
            painter.drawLine(p1, p2)

        # 2. Ambient Mint Glow Ring
        glow_rad = track_r + max(8.0, side * 0.035)
        glow_grad = QRadialGradient(QPointF(cx, cy), glow_rad)
        glow_grad.setColorAt(0.68, QColor(0, 0, 0, 0))
        glow_grad.setColorAt(0.88, COLOR_MINT_DIM)
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), glow_rad, glow_rad)

        # 3. Main Speedometer Gauge Track
        gauge_rect = QRectF(cx - track_r, cy - track_r, track_r * 2, track_r * 2)
        pen_track = QPen(COLOR_GAUGE_TRACK, track_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        painter.setPen(pen_track)
        painter.drawArc(gauge_rect, int(start_angle_deg * 16), int(total_span_deg * 16))

        # 4. Inner Concentric Tachometer Arc
        tach_r = track_r - (side * 0.08)
        tach_w = max(2.5, min(6.0, side * 0.012))
        tach_rect = QRectF(cx - tach_r, cy - tach_r, tach_r * 2, tach_r * 2)
        painter.setPen(QPen(QColor(10, 28, 20, 200), tach_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        painter.drawArc(tach_rect, int(start_angle_deg * 16), int(total_span_deg * 16))

        if rpm_ratio > 0.01:
            tach_span = total_span_deg * rpm_ratio
            if rpm_ratio < 0.70:
                tach_col = COLOR_EMERALD_CYAN
            elif rpm_ratio < 0.90:
                tach_col = COLOR_AMBER
            else:
                tach_col = COLOR_SHIFT_RED
            pen_tach = QPen(tach_col, tach_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
            painter.setPen(pen_tach)
            painter.drawArc(tach_rect, int(start_angle_deg * 16), int(tach_span * 16))

        # 5. Precision Graduation Ticks & Numbers
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

        # 6. Active Speed Glowing Ribbon
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

            tip_angle = start_angle_deg + active_span_deg
            tip_rad = math.radians(-tip_angle)
            tip_x = cx + math.cos(tip_rad) * track_r
            tip_y = cy + math.sin(tip_rad) * track_r

            beacon_r = max(3.0, min(8.0, side * 0.012))
            painter.setBrush(QBrush(COLOR_TEXT_PRIMARY))
            painter.setPen(QPen(sweep_color, 2))
            painter.drawEllipse(QPointF(tip_x, tip_y), beacon_r, beacon_r)

        # 7. Inner Concentric Ring
        inner_r = track_r - (side * 0.16)
        pen_inner = QPen(QColor(18, 50, 38, 120), 1.0, Qt.PenStyle.DashLine)
        painter.setPen(pen_inner)
        painter.drawArc(
            QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2),
            int(start_angle_deg * 16),
            int(total_span_deg * 16),
        )

        # 8. Central Large Digital Speedometer Readout
        speed_int = int(round(self.current_val))
        font_speed_size = max(20, min(58, int(side * 0.120)))
        font_speed = QFont("Segoe UI", font_speed_size, QFont.Weight.Bold)
        painter.setFont(font_speed)
        painter.setPen(COLOR_TEXT_PRIMARY)

        speed_box_w = side * 0.65
        speed_box_h = side * 0.19
        speed_rect = QRectF(cx - (speed_box_w / 2.0), cy - side * 0.25, speed_box_w, speed_box_h)
        painter.drawText(speed_rect, Qt.AlignmentFlag.AlignCenter, f"{speed_int}")

        # 9. Speed Unit Label & Motor RPM Tag
        painter.setPen(COLOR_MINT)
        font_unit = QFont("Segoe UI", max(7, min(13, int(side * 0.024))), QFont.Weight.Bold)
        font_unit.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(1, int(side * 0.005)))
        painter.setFont(font_unit)
        unit_h = max(11.0, side * 0.040)
        unit_rect = QRectF(cx - side * 0.35, cy - side * 0.055, side * 0.70, unit_h)
        rpm_formatted = f"{effective_rpm:,}" if effective_rpm > 0 else f"{self.sub_val}"
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, f"{self.unit}   •   {rpm_formatted} RPM")

        # 10. Center Stage Race Gear Hub
        gear_hub_y = cy - (side * 0.020)
        gear_block_w = max(46.0, min(76.0, side * 0.16))
        gear_block_h = max(26.0, min(42.0, side * 0.088))
        gear_rect = QRectF(cx - (gear_block_w / 2.0), gear_hub_y, gear_block_w, gear_block_h)

        if self.transmission_mode == "MANUAL":
            accent_col = COLOR_CYAN
        elif self.active_gear == "R":
            accent_col = COLOR_SHIFT_RED
        elif self.active_gear == "N":
            accent_col = COLOR_AMBER
        elif self.active_gear == "P":
            accent_col = COLOR_TEXT_MUTED
        else:
            accent_col = COLOR_MINT

        painter.setBrush(QBrush(QColor(6, 16, 12, 240)))
        painter.setPen(QPen(accent_col, 1.8))
        painter.drawRoundedRect(gear_rect, 6, 6)

        mode_tag_rect = QRectF(gear_rect.left(), gear_rect.top() + 2, gear_rect.width(), gear_rect.height() * 0.30)
        painter.setPen(accent_col)
        font_mode_tag = QFont("Segoe UI", max(5, min(8, int(side * 0.016))), QFont.Weight.Bold)
        painter.setFont(font_mode_tag)
        painter.drawText(mode_tag_rect, Qt.AlignmentFlag.AlignCenter, self.transmission_mode)

        gear_num_rect = QRectF(gear_rect.left(), gear_rect.top() + gear_rect.height() * 0.26, gear_rect.width(), gear_rect.height() * 0.72)
        font_gear_hub = QFont("Segoe UI", max(13, min(24, int(side * 0.058))), QFont.Weight.Bold)
        painter.setFont(font_gear_hub)
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(gear_num_rect, Qt.AlignmentFlag.AlignCenter, self.active_gear)

        # 11. Transmission Selector Strip
        capsule_y = gear_hub_y + gear_block_h + max(4.0, side * 0.010)
        if self.transmission_mode == "MANUAL":
            gears = ["R", "N", "1", "2", "3", "4", "5", "6"]
        else:
            gears = ["P", "R", "N", "D", "B"]

        slot_w = max(13.0, min(26.0, (side * 0.42) / len(gears)))
        box_h = max(12.0, min(17.0, side * 0.036))
        total_gear_w = len(gears) * slot_w
        start_gx = cx - (total_gear_w / 2.0)

        capsule_rect = QRectF(start_gx - 4, capsule_y - 2, total_gear_w + 8, box_h + 4)
        painter.setBrush(QBrush(QColor(4, 12, 9, 210)))
        painter.setPen(QPen(QColor(18, 50, 38, 160), 1))
        painter.drawRoundedRect(capsule_rect, 5, 5)

        font_gear = QFont("Segoe UI", max(6, min(10, int(side * 0.020))), QFont.Weight.Bold)
        painter.setFont(font_gear)

        for idx, g in enumerate(gears):
            gx = start_gx + idx * slot_w
            slot_rect = QRectF(gx, capsule_y, slot_w, box_h)

            is_active = False
            label_text = g
            if self.transmission_mode == "MANUAL":
                is_active = (g == self.active_gear)
            else:
                if self.active_gear.startswith("D"):
                    is_active = (g == "D")
                    if is_active and len(self.active_gear) > 1:
                        label_text = self.active_gear
                else:
                    is_active = (g == self.active_gear)

            if is_active:
                active_pill = QRectF(gx + 1.5, capsule_y + 1, slot_w - 3, box_h - 2)
                highlight_col = COLOR_CYAN if self.transmission_mode == "MANUAL" else COLOR_MINT
                painter.setBrush(QBrush(QColor(highlight_col.red(), highlight_col.green(), highlight_col.blue(), 55)))
                painter.setPen(QPen(highlight_col, 1.5))
                painter.drawRoundedRect(active_pill, 4, 4)
                painter.setPen(COLOR_TEXT_PRIMARY)
            else:
                painter.setPen(COLOR_TEXT_MUTED)

            painter.drawText(slot_rect, Qt.AlignmentFlag.AlignCenter, label_text)

        # 12. Racing Telemetry Meters for Throttle & Brake
        pedal_y = capsule_y + box_h + max(14.0, side * 0.036)
        bar_w = max(40.0, min(68.0, side * 0.13))
        bar_h = max(6.0, min(10.0, side * 0.020))
        gap = max(8.0, side * 0.018)

        font_pedal_lbl = QFont("Segoe UI", max(6, min(8, int(side * 0.017))), QFont.Weight.Bold)
        painter.setFont(font_pedal_lbl)

        brk_bx = cx - gap - bar_w
        lbl_y = pedal_y - max(11.0, side * 0.026)
        lbl_h = max(10.0, side * 0.024)

        painter.setPen(COLOR_SHIFT_RED if self.brake_pct > 0 else COLOR_TEXT_MUTED)
        painter.drawText(QRectF(brk_bx, lbl_y, bar_w, lbl_h), Qt.AlignmentFlag.AlignCenter, f"BRK {int(self.brake_pct)}%")

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(QPen(QColor(255, 77, 109, 60), 0.8))
        painter.drawRoundedRect(QRectF(brk_bx, pedal_y, bar_w, bar_h), 2, 2)

        brk_fill = bar_w * (min(100.0, max(0.0, self.brake_pct)) / 100.0)
        if brk_fill > 0:
            painter.setBrush(QBrush(COLOR_SHIFT_RED))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(brk_bx + bar_w - brk_fill, pedal_y, brk_fill, bar_h), 2, 2)

        thr_bx = cx + gap
        painter.setPen(COLOR_MINT if self.throttle_pct > 0 else COLOR_TEXT_MUTED)
        painter.drawText(QRectF(thr_bx, lbl_y, bar_w, lbl_h), Qt.AlignmentFlag.AlignCenter, f"THR {int(self.throttle_pct)}%")

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(QPen(QColor(0, 245, 160, 60), 0.8))
        painter.drawRoundedRect(QRectF(thr_bx, pedal_y, bar_w, bar_h), 2, 2)

        thr_fill = bar_w * (min(100.0, max(0.0, self.throttle_pct)) / 100.0)
        if thr_fill > 0:
            thr_grad = QLinearGradient(thr_bx, 0, thr_bx + thr_fill, 0)
            thr_grad.setColorAt(0.0, COLOR_CYAN)
            thr_grad.setColorAt(1.0, COLOR_MINT)
            painter.setBrush(QBrush(thr_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(thr_bx, pedal_y, thr_fill, bar_h), 2, 2)

        # 13. Steering Wheel Angle Vector
        steer_y = pedal_y + bar_h + max(4.0, side * 0.010)
        angle = self.steering_angle
        steer_txt = f"STR ◄ {abs(int(angle))}°" if angle < -0.5 else (f"STR {int(angle)}° ►" if angle > 0.5 else "STR 0°")
        s_color = COLOR_CYAN if abs(angle) > 1.0 else COLOR_TEXT_MUTED

        painter.setPen(s_color)
        painter.setFont(QFont("Segoe UI", max(5, min(9, int(side * 0.017))), QFont.Weight.Bold))
        painter.drawText(QRectF(cx - 50, steer_y, 100, 12), Qt.AlignmentFlag.AlignCenter, steer_txt)


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
        self.cluster_theme = "OLED"
        self.palette: AmbientPalette = PALETTES["mint"]
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)
        self.setMinimumWidth(0)

    def set_palette(self, palette: AmbientPalette | str) -> None:
        self.palette = get_palette(palette)
        self.update()

    def set_cluster_theme(self, theme: str) -> None:
        self.cluster_theme = theme.upper().strip()
        self.update()

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
        return getattr(self, "palette", PALETTES["mint"]).primary

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

        if getattr(self, "cluster_theme", "OLED") != "OLED":
            painter.setBrush(QBrush(COLOR_PANEL_BG))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 1))
            painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 8, 8)

        # Header
        hdr_font_sz = max(7, min(11, int(w * 0.024)))
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        painter.drawText(QRectF(14, 8, w * 0.5, 18), Qt.AlignmentFlag.AlignLeft, "TIRE PRESSURE & TPMS")

        painter.setPen(self.palette.primary)
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
            if getattr(self, "cluster_theme", "OLED") == "OLED":
                painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
                painter.setPen(QPen(QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 140), 1.5))
            else:
                painter.setBrush(QBrush(QColor(10, 24, 18, 230)))
                painter.setPen(QPen(COLOR_PANEL_BORDER, 1.4))
            painter.drawRoundedRect(chassis_rect, 10, 10)

            # Windshield & cockpit details
            painter.setPen(QPen(QColor(self.palette.primary.red(), self.palette.primary.green(), self.palette.primary.blue(), 90), 1.2))
            painter.drawLine(int(cx - cw * 0.36), int(cy - ch * 0.18), int(cx + cw * 0.36), int(cy - ch * 0.18))
            painter.drawLine(int(cx - cw * 0.32), int(cy + ch * 0.22), int(cx + cw * 0.32), int(cy + ch * 0.22))

            # Battery Pack Glow in Floor
            batt_floor = QRectF(cx - cw * 0.32, cy - ch * 0.12, cw * 0.64, ch * 0.32)
            painter.setBrush(QBrush(self.palette.dim))
            painter.setPen(QPen(self.palette.border, 0.8))
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
                if getattr(self, "cluster_theme", "OLED") != "OLED":
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

                dash_pen = QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 60) if getattr(self, "cluster_theme", "OLED") == "OLED" else QColor(18, 50, 38, 140)
                painter.setPen(QPen(dash_pen, 1, Qt.PenStyle.DashLine))
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
    Powertrain Thermal Monitor (Motor, Inverter, Battery) in Cyber-Mint with modern flair.
    Features sculpted cyber-cards, micro-thermometer level bars, status badges, and dynamic glow.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.motor_temp = 0.0
        self.inverter_temp = 0.0
        self.batt_temp = 0.0
        self.unit_system = "IMPERIAL"
        self.palette: AmbientPalette = PALETTES["mint"]
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(32)
        self.setMinimumWidth(0)

    def set_palette(self, palette: AmbientPalette | str) -> None:
        self.palette = get_palette(palette)
        self.update()

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
        return getattr(self, "palette", PALETTES["mint"]).primary

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()
        items = [
            ("⚡ MOTOR", self.motor_temp, 75.0, 90.0, 105.0),
            ("⚡ INV", self.inverter_temp, 65.0, 80.0, 95.0),
            ("BATT", self.batt_temp, 42.0, 50.0, 60.0),
        ]

        col_w = w / len(items)
        lbl_font_sz = max(6, min(9, int(h * 0.22)))
        val_font_sz = max(8, min(14, int(h * 0.32)))

        for i, (label, temp_c, warn_th, crit_th, max_scale) in enumerate(items):
            box_x = i * col_w + 3
            box_w = col_w - 6
            color = self._temp_color(temp_c, warn_th, crit_th)

            # Sculpted cyber-card gradient background
            grad = QLinearGradient(box_x, 0, box_x, h)
            grad.setColorAt(0.0, QColor(10, 24, 18, 230))
            grad.setColorAt(1.0, QColor(5, 14, 10, 240))
            painter.setBrush(QBrush(grad))

            # Dynamic state-aware border glow
            pri_col = getattr(self, "palette", PALETTES["mint"]).primary
            border_col = QColor(color.red(), color.green(), color.blue(), 100 if color == pri_col else 180)
            painter.setPen(QPen(border_col, 1))
            painter.drawRoundedRect(QRectF(box_x, 0, box_w, h - 2), 6, 6)

            # Sensor Label (Left)
            painter.setPen(COLOR_TEXT_SECONDARY)
            painter.setFont(QFont("Segoe UI", lbl_font_sz, QFont.Weight.Bold))
            if "BATT" in label:
                # Dedicated vector battery icon: crisp, perfectly scaled, zero missing glyph boxes
                icon_h = max(7.0, min(10.0, lbl_font_sz * 1.05))
                icon_w = icon_h * 1.65
                icon_x = box_x + 8.0
                icon_y = 3.0 + (h * 0.35 - icon_h) / 2.0

                # Outer battery casing
                painter.setPen(QPen(COLOR_TEXT_SECONDARY, 1.1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(QRectF(icon_x, icon_y, icon_w - 2.5, icon_h), 1.5, 1.5)

                # Positive terminal nipple
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(COLOR_TEXT_SECONDARY))
                painter.drawRoundedRect(QRectF(icon_x + icon_w - 2.5, icon_y + icon_h * 0.26, 2.0, icon_h * 0.48), 0.6, 0.6)

                # Active charge level fill (tinted with card thermal state color)
                painter.setBrush(QBrush(color))
                fill_w = max(2.0, (icon_w - 5.5) * 0.72)
                painter.drawRoundedRect(QRectF(icon_x + 1.5, icon_y + 1.5, fill_w, icon_h - 3.0), 0.8, 0.8)

                # Text label right next to vector icon
                painter.setPen(COLOR_TEXT_SECONDARY)
                painter.drawText(
                    QRectF(icon_x + icon_w + 4.0, 3, box_w * 0.60 - (icon_w + 4.0), h * 0.35),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    "BATT",
                )
            else:
                painter.drawText(QRectF(box_x + 8, 3, box_w * 0.60, h * 0.35), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

            # Status Tag (Right): OK / WARM / HOT
            status_tag = "OK" if temp_c < warn_th else ("WARM" if temp_c < crit_th else "HOT")
            painter.setPen(color)
            painter.setFont(QFont("Segoe UI", max(5, min(7, int(h * 0.18))), QFont.Weight.Black))
            painter.drawText(QRectF(box_x + box_w * 0.55, 3, box_w * 0.45 - 8, h * 0.35), Qt.AlignmentFlag.AlignRight, status_tag)

            # Digital Temperature (Imperial Fahrenheit)
            is_imp = (getattr(self, "unit_system", "METRIC") == "IMPERIAL")
            disp_temp = (temp_c * 9.0 / 5.0 + 32.0) if is_imp else temp_c
            unit_sym = "°F" if is_imp else "°C"

            painter.setPen(color)
            painter.setFont(QFont("Consolas", val_font_sz, QFont.Weight.Bold))
            painter.drawText(
                QRectF(box_x + 8, h * 0.32, box_w - 16, h * 0.44),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{disp_temp:.1f}{unit_sym}",
            )

            # Micro Thermal Gauge Progress Bar
            bar_y = h - 6.0
            bar_h = 3.0
            bar_w = box_w - 16.0
            painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(box_x + 8, bar_y, bar_w, bar_h), 1.5, 1.5)

            t_ratio = max(0.0, min(1.0, temp_c / max(1.0, max_scale)))
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(box_x + 8, bar_y, bar_w * t_ratio, bar_h), 1.5, 1.5)

        painter.end()


class CompactSpeedPod(QWidget):
    """
    Compact digital speedometer & transmission pod for non-speedometer pages.
    Ensures vehicle speed, gear, RPM, pedals, and steering remain prominently visible
    when Battery, Powertrain, or TPMS hero views occupy the cluster.
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
        self.cluster_theme = "OLED"
        self.is_right_wing = False
        self.palette: AmbientPalette = PALETTES["mint"]
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)
        self.setMinimumWidth(170)
        self.setMaximumWidth(260)

    def set_palette(self, palette: AmbientPalette | str) -> None:
        self.palette = get_palette(palette)
        self.update()

    def set_right_wing(self, is_right: bool) -> None:
        self.is_right_wing = bool(is_right)
        self.update()

    def set_cluster_theme(self, theme: str) -> None:
        self.cluster_theme = theme.upper().strip()
        self.update()

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

        # Calculate effective RPM for numeric readout
        effective_rpm = self.motor_rpm
        if effective_rpm <= 0 and self.speed > 0.5:
            effective_rpm = int(min(8000.0, (self.speed / max(1.0, self.max_speed)) * 7200.0))

        # Panel styling based on cluster theme
        if getattr(self, "cluster_theme", "OLED") == "OLED":
            is_right = getattr(self, "is_right_wing", False)
            seam_x = 0.0 if is_right else (w - 1.0)
            seam_grad = QLinearGradient(seam_x, 0, seam_x, h)
            seam_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            seam_grad.setColorAt(0.2, QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 180))
            seam_grad.setColorAt(0.8, QColor(self.palette.primary.red(), self.palette.primary.green(), self.palette.primary.blue(), 180))
            seam_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(QPen(QBrush(seam_grad), 1.5))
            painter.drawLine(int(seam_x), 10, int(seam_x), int(h - 10))
        else:
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor(8, 20, 15, 245))
            grad.setColorAt(1.0, QColor(4, 10, 8, 250))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor(0, 245, 160, 75), 1))
            painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 8, 8)

        # Header: Icon + SPEED and Gear Pill
        hdr_y = 8.0
        hdr_font_sz = max(7, min(10, int(w * 0.040)))
        painter.setFont(QFont("Segoe UI", hdr_font_sz, QFont.Weight.Bold))
        painter.setPen(self.palette.primary)
        painter.drawText(QRectF(10, hdr_y, w * 0.45, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "⚡ SPEED")

        badge_str = f"{self.trans_mode} [{self.gear}]"
        painter.setPen(self.palette.secondary if self.trans_mode == "MANUAL" else self.palette.highlight)
        painter.setFont(QFont("Consolas", max(7, min(9, int(w * 0.038))), QFont.Weight.Bold))
        painter.drawText(QRectF(w * 0.35, hdr_y, w * 0.65 - 10, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, badge_str)

        content_h = h - (hdr_y + 18.0)

        # Radial speed glow behind digits
        glow_center = QPointF(w * 0.35, hdr_y + 18.0 + content_h * 0.24)
        radial = QRadialGradient(glow_center, w * 0.45)
        radial.setColorAt(0.0, self.palette.dim)
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(radial))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(glow_center, w * 0.45, content_h * 0.35)

        # Large Digital Speed Number + Unit
        spd_y = hdr_y + 18.0 + (content_h * 0.02)
        spd_h = content_h * 0.40

        font_spd_sz = max(24, min(42, int(content_h * 0.34)))
        painter.setFont(QFont("Segoe UI", font_spd_sz, QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_PRIMARY)
        spd_str = f"{int(round(self.speed))}"
        painter.drawText(QRectF(10, spd_y, w * 0.52, spd_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, spd_str)

        # Unit + RPM column on right
        font_unit_sz = max(8, min(12, int(content_h * 0.11)))
        painter.setFont(QFont("Segoe UI", font_unit_sz, QFont.Weight.Bold))
        painter.setPen(self.palette.primary)
        painter.drawText(QRectF(w * 0.52, spd_y + (spd_h * 0.10), w * 0.44, spd_h * 0.40), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.unit)

        font_rpm_sz = max(7, min(10, int(content_h * 0.09)))
        painter.setFont(QFont("Consolas", font_rpm_sz, QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(QRectF(w * 0.52, spd_y + (spd_h * 0.52), w * 0.44, spd_h * 0.40), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{effective_rpm} RPM")

        # Slim Neon Speed Progress Bar
        bar_y = spd_y + spd_h + 3.0
        bar_w = w - 20.0
        bar_h = max(5.0, min(8.0, content_h * 0.06))

        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(10, bar_y, bar_w, bar_h), 2.5, 2.5)

        spd_ratio = max(0.0, min(1.0, self.speed / max(1.0, self.max_speed)))
        if spd_ratio > 0.01:
            bar_grad = QLinearGradient(10, 0, 10 + bar_w * spd_ratio, 0)
            bar_grad.setColorAt(0.0, self.palette.secondary)
            bar_grad.setColorAt(1.0, self.palette.primary)
            painter.setBrush(QBrush(bar_grad))
            painter.drawRoundedRect(QRectF(10, bar_y, bar_w * spd_ratio, bar_h), 2.5, 2.5)

        # Bottom Mini Pedals & Steer Pod with illuminated input meters
        sub_y = h - max(28.0, min(40.0, h * 0.22))
        sub_h = h - sub_y - 6.0
        sub_rect = QRectF(8, sub_y, w - 16, sub_h)
        if getattr(self, "cluster_theme", "OLED") != "OLED":
            painter.setBrush(QBrush(QColor(6, 16, 12, 220)))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
            painter.drawRoundedRect(sub_rect, 4, 4)

        font_pedal = QFont("Consolas", max(6, min(9, int(sub_h * 0.38))), QFont.Weight.Bold)
        painter.setFont(font_pedal)

        col_w = (w - 20.0) / 3.0
        painter.setPen(self.palette.primary)
        painter.drawText(QRectF(8, sub_y, col_w, sub_h), Qt.AlignmentFlag.AlignCenter, f"THR {int(self.throttle_pct)}%")
        painter.setPen(COLOR_SHIFT_RED if self.brake_pct > 0 else COLOR_TEXT_MUTED)
        painter.drawText(QRectF(8 + col_w, sub_y, col_w, sub_h), Qt.AlignmentFlag.AlignCenter, f"BRK {int(self.brake_pct)}%")
        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(QRectF(8 + 2 * col_w, sub_y, col_w, sub_h), Qt.AlignmentFlag.AlignCenter, f"STR {int(self.steer_angle)}°")

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
        self.cluster_theme = "OLED"
        self.palette: AmbientPalette = PALETTES["mint"]
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(220)

    def set_palette(self, palette: AmbientPalette | str) -> None:
        self.palette = get_palette(palette)
        self.update()

    def set_cluster_theme(self, theme: str) -> None:
        self.cluster_theme = theme.upper().strip()
        self.update()

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

        if getattr(self, "cluster_theme", "OLED") != "OLED":
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
        s_color = COLOR_AMBER if self.current > 70.0 else (self.palette.secondary if self.current < -2.0 else self.palette.primary)
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
        bar_color = self.palette.primary if self.soc > 30.0 else (COLOR_AMBER if self.soc > 15.0 else COLOR_RED)
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
        rng_w = max(120.0, (w * 0.48) - rng_x)
        rng_y = arc_cy - (arc_r * 0.65)

        painter.setFont(QFont("Segoe UI", max(6, min(8, int(upper_h * 0.09))), QFont.Weight.DemiBold))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(rng_x, rng_y, rng_w, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "ESTIMATED RANGE")

        is_imp = (self.unit_system == "IMPERIAL")
        range_val = int(round(self.est_range_km * 0.621371)) if is_imp else int(round(self.est_range_km))
        unit_str = "mi" if is_imp else "km"

        painter.setFont(QFont("Segoe UI", max(14, min(24, int(upper_h * 0.22))), QFont.Weight.Bold))
        painter.setPen(self.palette.highlight)
        painter.drawText(QRectF(rng_x, rng_y + 16, rng_w, 28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{range_val} {unit_str}")

        # Right Section: Pack Diagnostics Summary Grid (4 chips)
        right_start_x = max(w * 0.50, rng_x + rng_w + 10.0)
        right_w = w - right_start_x - 14.0
        chip_w = (right_w - 8.0) / 2.0
        chip_h = (upper_h - 14.0) / 2.0

        chips = [
            ("CELL AVG", "4.15 V", self.palette.primary),
            ("HEALTH (SOH)", "100%", self.palette.highlight),
            ("CHARGE LIMIT", "90%", self.palette.secondary),
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
            if getattr(self, "cluster_theme", "OLED") != "OLED":
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
            ("NET POWER", f"{self.power_kw:+.1f} kW", self.palette.secondary if self.power_kw < 0 else self.palette.highlight, 0, 1),
            ("CONSUMPTION", "15.2 kWh/100km" if not is_imp else "24.5 kWh/100mi", COLOR_TEXT_PRIMARY, 1, 1),
        ]

        f_q_lbl = QFont("Segoe UI", max(6, min(9, int(quad_h * 0.28))), QFont.Weight.Bold)
        f_q_val = QFont("Consolas", max(8, min(14, int(quad_h * 0.40))), QFont.Weight.Bold)

        for title, val, color, col, row in quads:
            qx = 12.0 + col * (quad_w + 8.0)
            qy = grid_y + row * (quad_h + 6.0)
            q_rect = QRectF(qx, qy, quad_w, quad_h)

            if getattr(self, "cluster_theme", "OLED") != "OLED":
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
        self.cluster_theme = "OLED"
        self.palette: AmbientPalette = PALETTES["mint"]
        self.wave_points: List[Tuple[float, float]] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(220)

    def set_palette(self, palette: AmbientPalette | str) -> None:
        self.palette = get_palette(palette)
        self.update()

    def set_cluster_theme(self, theme: str) -> None:
        self.cluster_theme = theme.upper().strip()
        self.update()

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

        if getattr(self, "cluster_theme", "OLED") != "OLED":
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
        painter.setPen(self.palette.highlight)
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

        painter.setBrush(QBrush(self.palette.primary))
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

        painter.setBrush(QBrush(self.palette.highlight if self.rear_pct < 65.0 else COLOR_AMBER))
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
        painter.setPen(self.palette.secondary)
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
            painter.setBrush(QBrush(self.palette.secondary))
            painter.drawRoundedRect(QRectF(fill_x, pwr_bar_y, fill_w, pwr_bar_h), 2, 2)
        elif self.power_kw > 0.2:
            fill_w = (self.power_kw / self.max_kw) * (14.0 + pwr_bar_w - zero_x)
            painter.setBrush(QBrush(self.palette.primary if self.power_kw < 70.0 else COLOR_AMBER))
            painter.drawRoundedRect(QRectF(zero_x, pwr_bar_y, fill_w, pwr_bar_h), 2, 2)

        # Readout below bar
        painter.setFont(QFont("Consolas", max(7, min(10, int(sec2_h * 0.26))), QFont.Weight.Bold))
        painter.setPen(self.palette.highlight)
        painter.drawText(QRectF(w * 0.30, pwr_bar_y + pwr_bar_h + 2, w * 0.40, 14), Qt.AlignmentFlag.AlignCenter, f"{self.power_kw:+.1f} kW")

        # 3. Live Rolling Telemetry Waveform (Bottom 44%)
        sec3_y = sec2_y + sec2_h + 4.0
        sec3_h = h - sec3_y - 8.0
        wave_rect = QRectF(14, sec3_y, w - 28, sec3_h)

        if getattr(self, "cluster_theme", "OLED") != "OLED":
            painter.setBrush(QBrush(QColor(6, 14, 10, 190)))
            painter.setPen(QPen(COLOR_PANEL_BORDER, 0.8))
            painter.drawRoundedRect(wave_rect, 4, 4)

        painter.setFont(QFont("Segoe UI", max(6, min(8, int(sec3_h * 0.15))), QFont.Weight.Bold))
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(QRectF(20, sec3_y + 4, 120, 14), Qt.AlignmentFlag.AlignLeft, "LIVE TELEMETRY WAVE")

        painter.setPen(self.palette.primary)
        painter.drawText(QRectF(w - 96, sec3_y + 4, 34, 14), Qt.AlignmentFlag.AlignRight, "SPD")
        painter.setPen(COLOR_AMBER)
        painter.drawText(QRectF(w - 56, sec3_y + 4, 34, 14), Qt.AlignmentFlag.AlignRight, "PWR")

        # Draw Grid Line
        mid_y = sec3_y + (sec3_h * 0.55)
        dash_pen = QColor(self.palette.secondary.red(), self.palette.secondary.green(), self.palette.secondary.blue(), 60) if getattr(self, "cluster_theme", "OLED") == "OLED" else QColor(18, 50, 38, 120)
        painter.setPen(QPen(dash_pen, 1, Qt.PenStyle.DashLine))
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

            painter.setPen(QPen(self.palette.primary, 1.8))
            painter.drawPolyline(spd_poly)

            painter.setPen(QPen(COLOR_AMBER, 1.8))
            painter.drawPolyline(pwr_poly)

        painter.end()


class AnimatedStackedWidget(QStackedWidget):
    """
    High-end automotive sliding carousel stacked widget with smooth cubic easing
    and depth crossfade transitions between cockpit views.
    Supports directional horizontal transitions (Left / Right), rapid interruption
    handling, and instantaneous fallback for headless tests or unmapped windows.
    """
    animation_finished = pyqtSignal(int)  # Emits current index when transition completes

    def __init__(self, parent: Optional[QWidget] = None, duration_ms: int = 260):
        super().__init__(parent)
        self.duration_ms = duration_ms
        self._animation_enabled: bool = True
        self._target_index: int = 0
        self._is_animating: bool = False
        self._anim_group: Optional[QParallelAnimationGroup] = None
        self._active_widgets: List[QWidget] = []

    def set_animation_enabled(self, enabled: bool) -> None:
        """Enables or disables view transition animations."""
        self._animation_enabled = bool(enabled)
        if not self._animation_enabled and self._is_animating:
            self.finish_animation()

    def is_animation_enabled(self) -> bool:
        return self._animation_enabled

    def currentIndex(self) -> int:
        if self._is_animating:
            return self._target_index
        return super().currentIndex()

    def currentWidget(self) -> Optional[QWidget]:
        if self._is_animating:
            return self.widget(self._target_index)
        return super().currentWidget()

    def setCurrentIndex(self, index: int) -> None:
        """Immediate set index without animation."""
        self.finish_animation()
        self._target_index = index
        super().setCurrentIndex(index)

    def finish_animation(self) -> None:
        """Immediately settles any in-flight slide animation."""
        if self._anim_group is not None:
            try:
                self._anim_group.stop()
            except Exception:
                pass
            self._anim_group = None
        for w in self._active_widgets:
            try:
                w.setGraphicsEffect(None)
                w.move(0, 0)
            except Exception:
                pass
        self._active_widgets.clear()
        if self._is_animating:
            self._is_animating = False
            super().setCurrentIndex(self._target_index)
            self.animation_finished.emit(self._target_index)

    def slide_to_index(
        self,
        next_index: int,
        direction: Optional[str] = None,
        animated: bool = True,
    ) -> None:
        """
        Transitions to next_index with a smooth horizontal slide and crossfade.
        direction: "RIGHT" (slides left, enters from right) or "LEFT" (slides right, enters from left).
        """
        count = self.count()
        if count <= 0:
            return
        next_index = max(0, min(next_index, count - 1))
        curr_index = self.currentIndex()

        if next_index == curr_index and not self._is_animating:
            return

        # Settle any running animation first
        if self._is_animating:
            self.finish_animation()
            curr_index = super().currentIndex()
            if next_index == curr_index:
                return

        # Settle instantly if animations disabled, widget hidden, or zero size
        if (
            not self._animation_enabled
            or not self.isVisible()
            or self.width() <= 10
            or not animated
            or self.duration_ms <= 0
        ):
            self._target_index = next_index
            super().setCurrentIndex(next_index)
            return

        curr_widget = self.widget(curr_index)
        next_widget = self.widget(next_index)
        if not curr_widget or not next_widget or curr_widget == next_widget:
            self._target_index = next_index
            super().setCurrentIndex(next_index)
            return

        # Determine slide direction
        if direction is None:
            direction = "RIGHT" if next_index > curr_index else "LEFT"
        else:
            direction = str(direction).upper().strip()

        w = self.width()
        h = self.height()
        offset_x = w if direction == "RIGHT" else -w

        self._target_index = next_index
        self._is_animating = True
        self._active_widgets = [curr_widget, next_widget]

        # Position incoming widget off-screen
        next_widget.setGeometry(offset_x, 0, w, h)
        next_widget.setVisible(True)
        next_widget.raise_()

        # Apply depth crossfade graphics effects
        eff_curr = QGraphicsOpacityEffect(curr_widget)
        curr_widget.setGraphicsEffect(eff_curr)
        eff_curr.setOpacity(1.0)

        eff_next = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(eff_next)
        eff_next.setOpacity(0.2)

        group = QParallelAnimationGroup(self)

        # Outgoing widget position animation: 0 -> -offset_x
        anim_pos_curr = QPropertyAnimation(curr_widget, b"pos")
        anim_pos_curr.setDuration(self.duration_ms)
        anim_pos_curr.setStartValue(QPoint(0, 0))
        anim_pos_curr.setEndValue(QPoint(-offset_x, 0))
        anim_pos_curr.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(anim_pos_curr)

        # Outgoing widget opacity animation: 1.0 -> 0.15
        anim_op_curr = QPropertyAnimation(eff_curr, b"opacity")
        anim_op_curr.setDuration(self.duration_ms)
        anim_op_curr.setStartValue(1.0)
        anim_op_curr.setEndValue(0.15)
        anim_op_curr.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(anim_op_curr)

        # Incoming widget position animation: offset_x -> 0
        anim_pos_next = QPropertyAnimation(next_widget, b"pos")
        anim_pos_next.setDuration(self.duration_ms)
        anim_pos_next.setStartValue(QPoint(offset_x, 0))
        anim_pos_next.setEndValue(QPoint(0, 0))
        anim_pos_next.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(anim_pos_next)

        # Incoming widget opacity animation: 0.2 -> 1.0
        anim_op_next = QPropertyAnimation(eff_next, b"opacity")
        anim_op_next.setDuration(self.duration_ms)
        anim_op_next.setStartValue(0.2)
        anim_op_next.setEndValue(1.0)
        anim_op_next.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(anim_op_next)

        def _on_done():
            self.finish_animation()

        group.finished.connect(_on_done)
        self._anim_group = group
        group.start()

    def resizeEvent(self, event) -> None:
        if self._is_animating:
            self.finish_animation()
        super().resizeEvent(event)


class TripHeaderLabel(QLabel):
    """
    Trip odometer header label featuring a crisp, anti-aliased vector navigation
    pin icon rendered with QPainter in neon cyber-mint (#00F5A0).
    Guarantees reliable, high-resolution rendering with zero missing-glyph tofu boxes (□)
    across all platforms, fonts, and embedded display environments.
    """
    def __init__(self, text: str = "TRIP", parent=None):
        super().__init__(text, parent)
        self._raw_title = text.replace("📍", "").strip()

    def setText(self, text: str) -> None:
        self._raw_title = text.replace("📍", "").strip()
        super().setText(text)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        h = float(self.height())
        font = self.font()
        painter.setFont(font)

        # Scale pin icon proportionally with font size
        pt_sz = font.pointSizeF() if font.pointSizeF() > 0 else float(font.pointSize())
        icon_h = max(8.0, min(14.0, pt_sz * 1.35))
        pin_r = icon_h * 0.36
        pin_x = pin_r + 1.0
        pin_y = max(1.0, (h - icon_h) / 2.0)

        # Draw smooth location pin path
        path = QPainterPath()
        path.moveTo(pin_x, pin_y + icon_h)
        path.cubicTo(pin_x - pin_r * 1.15, pin_y + icon_h * 0.5, pin_x - pin_r, pin_y + pin_r * 1.2, pin_x - pin_r, pin_y + pin_r)
        path.arcTo(pin_x - pin_r, pin_y, pin_r * 2.0, pin_r * 2.0, 180, -180)
        path.cubicTo(pin_x + pin_r, pin_y + pin_r * 1.2, pin_x + pin_r * 1.15, pin_y + icon_h * 0.5, pin_x, pin_y + icon_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(COLOR_MINT))
        painter.fillPath(path, COLOR_MINT)

        # Inner hole
        painter.setBrush(QBrush(QColor(6, 18, 14)))
        painter.drawEllipse(QPointF(pin_x, pin_y + pin_r), pin_r * 0.42, pin_r * 0.42)

        # Text label
        painter.setPen(COLOR_MINT)
        text_x = pin_x + pin_r + 5.0
        title = self._raw_title if self._raw_title else "TRIP"
        painter.drawText(
            QRectF(text_x, 0, max(0.0, float(self.width()) - text_x), h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )
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
        self.cluster_theme = "OLED"
        self.palette: AmbientPalette = PALETTES["mint"]
        self.palette_key: str = "mint"
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

        # Streamlined, distraction-free Top Layout (Speed box removed; side CompactSpeedPod active across all pages)
        self.top_layout.addWidget(self.left_blinker)
        self.top_layout.addWidget(self.brand_label)
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
        self.page_stack = AnimatedStackedWidget(duration_ms=260)
        self.page_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Page 0: Full-Width Speedometer Dial (MPH)
        self.speed_page = SpeedometerDialWidget(min_val=0.0, max_val=120.0, title="SPEED", unit="MPH")
        self.page_stack.addWidget(self.speed_page)      # Index 0

        # Dedicated Compact Speed Views for all non-speedometer pages
        self.battery_speed_pod = CompactSpeedPod()
        self.powertrain_speed_pod = CompactSpeedPod()
        self.tpms_speed_pod = CompactSpeedPod()
        self.compact_speed_pods = [self.battery_speed_pod, self.powertrain_speed_pod, self.tpms_speed_pod]
        self.compact_speed_widget = self.battery_speed_pod

        # Page 1: Battery & Energy Diagnostics + Compact Speed View
        self.battery_page = BatteryHeroWidget()
        self.page1_container = QWidget()
        self.page1_layout = QHBoxLayout(self.page1_container)
        self.page1_layout.setContentsMargins(0, 0, 0, 0)
        self.page1_layout.setSpacing(8)
        self.page1_layout.addWidget(self.battery_speed_pod)
        self.page1_layout.addWidget(self.battery_page, stretch=1)
        self.page_stack.addWidget(self.page1_container)    # Index 1

        # Page 2: Powertrain Dynamics & AWD + Compact Speed View
        self.powertrain_page = PowertrainHeroWidget()
        self.page2_container = QWidget()
        self.page2_layout = QHBoxLayout(self.page2_container)
        self.page2_layout.setContentsMargins(0, 0, 0, 0)
        self.page2_layout.setSpacing(8)
        self.page2_layout.addWidget(self.powertrain_speed_pod)
        self.page2_layout.addWidget(self.powertrain_page, stretch=1)
        self.page_stack.addWidget(self.page2_container) # Index 2

        # Page 3: 4-Wheel TPMS Monitoring + Compact Speed View
        self.tpms_page = TPMSWidget()
        self.page3_container = QWidget()
        self.page3_layout = QHBoxLayout(self.page3_container)
        self.page3_layout.setContentsMargins(0, 0, 0, 0)
        self.page3_layout.setSpacing(8)
        self.page3_layout.addWidget(self.tpms_speed_pod)
        self.page3_layout.addWidget(self.tpms_page, stretch=1)
        self.page_stack.addWidget(self.page3_container)       # Index 3

        self.main_layout.addWidget(self.page_stack, stretch=1)

        # Aliases for core widgets
        self.center_stack = self.page_stack
        self.speed_gauge = self.speed_page
        self.battery_hero = self.battery_page
        self.powertrain_hero = self.powertrain_page
        self.tpms_widget = self.tpms_page

        # Sync initial theme to hero widgets and pods
        self.battery_hero.set_cluster_theme(self.cluster_theme)
        self.powertrain_hero.set_cluster_theme(self.cluster_theme)
        self.tpms_widget.set_cluster_theme(self.cluster_theme)
        for pod in self.compact_speed_pods:
            pod.set_cluster_theme(self.cluster_theme)

        # Preserved widgets and dummy hierarchies for legacy telemetry / test assertions
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
        dummy_spd = QWidget()
        self.wing_1_top_stack.addWidget(dummy_spd)

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
        self.bottom_bar.setStyleSheet(
            "background-color: rgba(4, 14, 10, 0.75); border-top: 1px solid rgba(0, 245, 160, 0.25); "
            "border-radius: 6px; padding: 2px;"
        )
        self.bottom_layout = QHBoxLayout(self.bottom_bar)
        self.bottom_layout.setContentsMargins(6, 2, 6, 2)
        self.bottom_layout.setSpacing(10)

        # Unified Single-Pod Trip Odometer with modern cyber flair
        self.trip_pod = QFrame()
        self.trip_pod.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(10, 26, 20, 0.95), stop:1 rgba(6, 16, 12, 0.95)); "
            "border: 1px solid rgba(0, 245, 160, 0.35); border-radius: 6px;"
        )
        self.trip_layout = QVBoxLayout(self.trip_pod)
        self.trip_layout.setContentsMargins(8, 2, 8, 2)
        self.trip_layout.setSpacing(0)

        self.trip_hdr = TripHeaderLabel("TRIP")
        self.trip_hdr.setStyleSheet("color: #00F5A0; font-weight: bold; border: none; background: transparent; letter-spacing: 0.5px;")

        self.trip_dist_val = QLabel("0.00 mi")
        self.trip_dist_val.setStyleSheet("color: #FFFFFF; font-weight: bold; font-family: Consolas; border: none; background: transparent;")

        self.trip_layout.addWidget(self.trip_hdr)
        self.trip_layout.addWidget(self.trip_dist_val)
        self.bottom_layout.addWidget(self.trip_pod)

        # Thermal Diagnostics Pods with sculpted cyber-cards
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
        self._apply_cluster_theme_styles()

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

        bot_h = max(42, min(64, int(46 * scale)))
        self.bottom_bar.setFixedHeight(bot_h)

        pod_w = max(180, min(260, int(w * 0.28)))
        for sp in getattr(self, "compact_speed_pods", []):
            sp.setFixedWidth(pod_w)

        self.trip_pod.setFixedWidth(max(105, min(170, int(130 * scale))))

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
            self.controls_hint.setText("[KEYS: 1:RACE | 2:SIM | 3:TEST | V:VIEW | X:SWAP | B:THEME | T:TRANS | E/C:SHIFT | U:UNITS | L:LOG]")
        elif mode == "SIMULATION":
            self.op_mode_badge.setText("SIMULATION [GAME]")
            self.op_mode_badge.setStyleSheet(
                "background-color: rgba(0, 229, 255, 0.22); color: #00E5FF; padding: 2px 10px; border-radius: 4px; border: 1px solid #00E5FF; font-weight: bold;"
            )
            self.controls_hint.setText("[V:VIEW | X:SWAP | B:THEME | T:TRANS | W/S:PEDALS | A/D:STEER | E/C:SHIFT | U:UNITS | L:LOG | M:MODE]")
        elif mode == "TEST":
            self.op_mode_badge.setText("TEST [MOCK]")
            self.op_mode_badge.setStyleSheet(
                "background-color: rgba(154, 230, 180, 0.20); color: #5CFFC7; padding: 2px 10px; border-radius: 4px; border: 1px solid #5CFFC7; font-weight: bold;"
            )
            self.controls_hint.setText("[TEST: AUTO ONLY | V:VIEW | X:SWAP | B:THEME | 1:RACE | 2:SIM | U:UNITS | L:LOG | SPACE:PAUSE]")

    def _flash_nav_btn(self, btn: QPushButton) -> None:
        """Briefly flashes chevron button for tactile visual feedback."""
        if not self.isVisible():
            return
        try:
            btn.setStyleSheet(
                "QPushButton { color: #FFFFFF; background: rgba(0, 245, 160, 0.35); border-radius: 3px; font-weight: bold; font-size: 10pt; }"
            )
            QTimer.singleShot(
                150,
                btn,
                lambda: btn.setStyleSheet(
                    "QPushButton { color: #00F5A0; background: transparent; border: none; font-weight: bold; font-size: 10pt; } "
                    "QPushButton:hover { color: #FFFFFF; }"
                ),
            )
        except Exception:
            pass

    def set_animation_enabled(self, enabled: bool) -> None:
        """Enables or disables view transition slide animations."""
        if hasattr(self, "page_stack") and hasattr(self.page_stack, "set_animation_enabled"):
            self.page_stack.set_animation_enabled(enabled)

    PAGE_NAMES = ["SPEED", "BATTERY", "POWERTRAIN", "TPMS"]

    def set_page(self, index: int, direction: Optional[str] = None, animated: bool = True) -> None:
        """Sets the active full-width page in the main cluster stack with smooth slide animation."""
        prev_idx = self.current_page_idx
        self.current_page_idx = index % len(self.PAGE_NAMES)
        p_name = self.PAGE_NAMES[self.current_page_idx]
        self.active_hero_view = p_name

        if direction is None:
            if self.current_page_idx > prev_idx:
                direction = "RIGHT"
            elif self.current_page_idx < prev_idx:
                direction = "LEFT"

        if hasattr(self.page_stack, "slide_to_index"):
            self.page_stack.slide_to_index(self.current_page_idx, direction=direction, animated=animated)
        else:
            self.page_stack.setCurrentIndex(self.current_page_idx)

        swap_suffix = " [⇄]" if self.swap_wings else ""
        self.page_title_label.setText(f"◄ {p_name} [{self.current_page_idx+1}/4]{swap_suffix} ►")

        # Ensure container children are properly visible
        if hasattr(self, "battery_speed_pod"):
            self.battery_speed_pod.setVisible(True)
            self.battery_page.setVisible(True)
            self.powertrain_speed_pod.setVisible(True)
            self.powertrain_page.setVisible(True)
            self.tpms_speed_pod.setVisible(True)
            self.tpms_page.setVisible(True)

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
            self.speed_hud_badge.setVisible(False)
            self.ready_badge.setVisible(False)
            self.wing_1_top_stack.setCurrentIndex(1)
            self.wing_2_stack.setCurrentIndex(0)
        elif p_name == "POWERTRAIN":
            self.nav_frame.setStyleSheet("background-color: rgba(26, 20, 6, 0.9); border: 1px solid rgba(255, 184, 0, 0.5); border-radius: 4px;")
            self.page_title_label.setStyleSheet("color: #FFB800; font-weight: bold; font-size: 8pt;")
            self.speed_hud_badge.setVisible(False)
            self.ready_badge.setVisible(False)
            self.wing_1_top_stack.setCurrentIndex(1)
            self.wing_2_stack.setCurrentIndex(1)
        elif p_name == "TPMS":
            self.nav_frame.setStyleSheet("background-color: rgba(12, 26, 20, 0.9); border: 1px solid rgba(92, 255, 199, 0.4); border-radius: 4px;")
            self.page_title_label.setStyleSheet("color: #5CFFC7; font-weight: bold; font-size: 8pt;")
            self.speed_hud_badge.setVisible(False)
            self.ready_badge.setVisible(False)
            self.wing_1_top_stack.setCurrentIndex(1)
            self.wing_2_stack.setCurrentIndex(0)

        if hasattr(self, "_last_record") and self._last_record is not None:
            self.update_telemetry(self._last_record)

        self.hero_view_changed.emit(self.active_hero_view)

    def next_page(self) -> None:
        """Navigates to the next widget page (Right) with slide animation."""
        if hasattr(self, "nav_next_btn"):
            self._flash_nav_btn(self.nav_next_btn)
        self.set_page(self.current_page_idx + 1, direction="RIGHT")

    def prev_page(self) -> None:
        """Navigates to the previous widget page (Left) with slide animation."""
        if hasattr(self, "nav_prev_btn"):
            self._flash_nav_btn(self.nav_prev_btn)
        self.set_page(self.current_page_idx - 1, direction="LEFT")

    def set_hero_view(self, view_name: str) -> None:
        """Sets the active widget page in the central stack by name."""
        v = view_name.upper().strip()
        mapping = {"SPEED": 0, "BATTERY": 1, "BATT": 1, "POWERTRAIN": 2, "PWR": 2, "TPMS": 3}
        target = mapping.get(v, 0)
        direction = "RIGHT" if target >= self.current_page_idx else "LEFT"
        self.set_page(target, direction=direction)

    def cycle_hero_view(self) -> str:
        """Cycles to the next widget page."""
        self.next_page()
        return self.active_hero_view

    def toggle_wing_swap(self) -> bool:
        """Toggles the left and right wing layout positions."""
        self.set_wing_swap(not self.swap_wings)
        return self.swap_wings

    def set_wing_swap(self, swap: bool) -> None:
        """Sets whether compact speed pod and hero widget positions are swapped."""
        self.swap_wings = bool(swap)
        if hasattr(self, "page1_layout") and hasattr(self, "page2_layout") and hasattr(self, "page3_layout"):
            while self.page1_layout.count():
                self.page1_layout.takeAt(0)
            while self.page2_layout.count():
                self.page2_layout.takeAt(0)
            while self.page3_layout.count():
                self.page3_layout.takeAt(0)

            if not self.swap_wings:
                self.page1_layout.addWidget(self.battery_speed_pod)
                self.page1_layout.addWidget(self.battery_page, stretch=1)
                self.page2_layout.addWidget(self.powertrain_speed_pod)
                self.page2_layout.addWidget(self.powertrain_page, stretch=1)
                self.page3_layout.addWidget(self.tpms_speed_pod)
                self.page3_layout.addWidget(self.tpms_page, stretch=1)
            else:
                self.page1_layout.addWidget(self.battery_page, stretch=1)
                self.page1_layout.addWidget(self.battery_speed_pod)
                self.page2_layout.addWidget(self.powertrain_page, stretch=1)
                self.page2_layout.addWidget(self.powertrain_speed_pod)
                self.page3_layout.addWidget(self.tpms_page, stretch=1)
                self.page3_layout.addWidget(self.tpms_speed_pod)

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

        for pod in getattr(self, "compact_speed_pods", []):
            if hasattr(pod, "set_right_wing"):
                pod.set_right_wing(self.swap_wings)

        self.set_page(self.current_page_idx)
        self.wing_swap_changed.emit(self.swap_wings)

    def set_palette(self, palette: AmbientPalette | str) -> str:
        """Sets active ambient colorway palette and propagates to all child widgets."""
        pal = get_palette(palette)
        self.palette = pal
        for k, v in PALETTES.items():
            if v.name == pal.name:
                self.palette_key = k
                break
        else:
            self.palette_key = "mint"

        if hasattr(self, "speed_gauge") and hasattr(self.speed_gauge, "set_palette"):
            self.speed_gauge.set_palette(pal)
        if hasattr(self, "battery_hero") and hasattr(self.battery_hero, "set_palette"):
            self.battery_hero.set_palette(pal)
        if hasattr(self, "powertrain_hero") and hasattr(self.powertrain_hero, "set_palette"):
            self.powertrain_hero.set_palette(pal)
        if hasattr(self, "tpms_widget") and hasattr(self.tpms_widget, "set_palette"):
            self.tpms_widget.set_palette(pal)
        if hasattr(self, "thermal_widget") and hasattr(self.thermal_widget, "set_palette"):
            self.thermal_widget.set_palette(pal)
        if hasattr(self, "compact_speed_widget") and hasattr(self.compact_speed_widget, "set_palette"):
            self.compact_speed_widget.set_palette(pal)
        for pod in getattr(self, "compact_speed_pods", []):
            if hasattr(pod, "set_palette"):
                pod.set_palette(pal)
        self._apply_cluster_theme_styles()
        return self.palette_key

    def cycle_palette(self) -> str:
        """Cycles through the 5 signature OLED ambient palettes in sequence."""
        if getattr(self, "cluster_theme", "OLED") != "OLED":
            self.set_cluster_theme("OLED")

        try:
            curr_idx = PALETTE_KEYS.index(self.palette_key)
            next_key = PALETTE_KEYS[(curr_idx + 1) % len(PALETTE_KEYS)]
        except (ValueError, IndexError):
            next_key = PALETTE_KEYS[0]

        self.set_palette(next_key)

        # Trigger centered floating speedometer glassmorphic overlay
        if hasattr(self, "speed_gauge") and hasattr(self.speed_gauge, "show_palette_toast"):
            self.speed_gauge.show_palette_toast(self.palette.name)

        # Trigger top HUD ribbon status badge
        if hasattr(self, "status_badge"):
            p_col = self.palette.primary.name()
            self.status_badge.setText(f"🎨 PALETTE: {self.palette.name}")
            self.status_badge.setStyleSheet(
                f"color: {p_col}; background-color: rgba(0, 0, 0, 0.85); "
                f"border: 1px solid {p_col}; padding: 2px 8px; border-radius: 4px; "
                f"font-weight: bold; font-family: 'Segoe UI'; font-size: 8.5pt;"
            )
            self.status_badge.setVisible(True)
            QTimer.singleShot(
                1800,
                lambda: self.status_badge.setVisible(False) if not (hasattr(self, "_last_record") and self._last_record and self._last_record.warnings) else None,
            )
        return self.palette_key

    def set_cluster_theme(self, theme: str) -> None:
        """Sets the visual theme for the cluster ('OLED' or 'CLASSIC')."""
        self.cluster_theme = theme.upper().strip()
        if hasattr(self, "speed_gauge") and hasattr(self.speed_gauge, "set_cluster_theme"):
            self.speed_gauge.set_cluster_theme(self.cluster_theme)
        for pod in getattr(self, "compact_speed_pods", []):
            if hasattr(pod, "set_cluster_theme"):
                pod.set_cluster_theme(self.cluster_theme)
        for hero in (getattr(self, "battery_hero", None), getattr(self, "powertrain_hero", None), getattr(self, "tpms_widget", None)):
            if hero and hasattr(hero, "set_cluster_theme"):
                hero.set_cluster_theme(self.cluster_theme)
        self._apply_cluster_theme_styles()

    def toggle_cluster_theme(self) -> str:
        """Toggles between OLED Beta theme and Classic theme."""
        new_theme = "CLASSIC" if self.cluster_theme == "OLED" else "OLED"
        self.set_cluster_theme(new_theme)
        if hasattr(self, "status_badge"):
            self.status_badge.setText(f"THEME: {self.cluster_theme} BETA" if self.cluster_theme == "OLED" else "THEME: CLASSIC")
            self.status_badge.setVisible(True)
            QTimer.singleShot(
                2000,
                lambda: self.status_badge.setVisible(False) if not (hasattr(self, "_last_record") and self._last_record and self._last_record.warnings) else None,
            )
        return self.cluster_theme

    def _apply_cluster_theme_styles(self) -> None:
        """Applies global styling tokens matching the active cluster theme."""
        if getattr(self, "cluster_theme", "OLED") == "OLED":
            pal = getattr(self, "palette", PALETTES["mint"])
            p_sec = pal.secondary
            top_border = f"rgba({p_sec.red()}, {p_sec.green()}, {p_sec.blue()}, 0.35)"
            bot_border = f"rgba({p_sec.red()}, {p_sec.green()}, {p_sec.blue()}, 0.25)"
            trip_border = f"rgba({p_sec.red()}, {p_sec.green()}, {p_sec.blue()}, 0.45)"

            self.setStyleSheet(
                """
                QMainWindow {
                    background-color: #000000;
                }
                QWidget {
                    color: #FFFFFF;
                }
                """
            )
            if hasattr(self, "top_bar"):
                self.top_bar.setStyleSheet(f"background-color: #000000; border-bottom: 1px solid {top_border}; border-radius: 4px;")
            if hasattr(self, "bottom_bar"):
                self.bottom_bar.setStyleSheet(
                    f"background-color: #000000; border-top: 1px solid {bot_border}; border-radius: 6px; padding: 2px;"
                )
            if hasattr(self, "trip_pod"):
                self.trip_pod.setStyleSheet(
                    f"background-color: #000000; border: 1px solid {trip_border}; border-radius: 6px;"
                )
        else:
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
            if hasattr(self, "top_bar"):
                self.top_bar.setStyleSheet("background-color: rgba(4, 12, 8, 0.65); border-bottom: 1px solid rgba(0, 245, 160, 0.2); border-radius: 4px;")
            if hasattr(self, "bottom_bar"):
                self.bottom_bar.setStyleSheet(
                    "background-color: rgba(4, 14, 10, 0.75); border-top: 1px solid rgba(0, 245, 160, 0.25); border-radius: 6px; padding: 2px;"
                )
            if hasattr(self, "trip_pod"):
                self.trip_pod.setStyleSheet(
                    "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(10, 26, 20, 0.95), stop:1 rgba(6, 16, 12, 0.95)); border: 1px solid rgba(0, 245, 160, 0.35); border-radius: 6px;"
                )

    def toggle_units(self) -> str:
        """In v4.1.0+, system is locked to IMPERIAL; returns active unit system."""
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
        for sp in getattr(self, "compact_speed_pods", [self.compact_speed_widget]):
            sp.set_unit_system("IMPERIAL")
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
        if hasattr(self.speed_gauge, "set_aux_telemetry"):
            disp_dist = record.trip_distance_km * 0.621371
            self.speed_gauge.set_aux_telemetry(
                soc=record.battery_soc,
                motor_temp_c=record.motor_temp_c,
                inverter_temp_c=record.inverter_temp_c,
                trip_dist_mi=disp_dist,
                battery_voltage=getattr(record, "battery_voltage", 398.0),
                battery_power_kw=getattr(record, "battery_power_kw", 42.0),
            )

        # Compact Speed Pods (for non-speed hero views)
        for pod in getattr(self, "compact_speed_pods", [self.compact_speed_widget]):
            pod.set_speed_and_status(
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

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if hasattr(self, "speed_gauge") and hasattr(self.speed_gauge, "startup_needle_sweep"):
            self.speed_gauge.startup_needle_sweep()

    def keyPressEvent(self, event) -> None:
        """Handles mode switching, auto/manual transmission, and video-game controls."""
        key = event.key()

        # Interupt startup needle sweep on interactive driving/navigation input
        if hasattr(self, "speed_gauge") and hasattr(self.speed_gauge, "finish_sweep"):
            self.speed_gauge.finish_sweep()

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
        elif key == Qt.Key.Key_B:
            self.toggle_cluster_theme()
            return
        elif key == Qt.Key.Key_P:
            self.cycle_palette()
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
