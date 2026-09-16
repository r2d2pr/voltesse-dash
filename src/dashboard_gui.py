"""
Voltesse Dash - PyQt6 Driver GUI
A high-contrast, distraction-free digital cockpit instrument cluster.
Designed for embedded Raspberry Pi automotive display deployments.
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


# Color Palette Constants (Futuristic High-Contrast Automotive Theme)
COLOR_BG_DARK = QColor("#080B10")
COLOR_CARD_BG = QColor("#111622")
COLOR_CARD_BORDER = QColor("#1E293B")
COLOR_CYAN = QColor("#00E5FF")
COLOR_BLUE = QColor("#2979FF")
COLOR_GREEN = QColor("#00E676")
COLOR_AMBER = QColor("#FFAB00")
COLOR_RED = QColor("#FF1744")
COLOR_TEXT_PRIMARY = QColor("#F8FAFC")
COLOR_TEXT_MUTED = QColor("#64748B")
COLOR_GAUGE_TRACK = QColor("#1A2234")


class ArcGaugeWidget(QWidget):
    """
    High-performance custom QPainter arc gauge.
    Displays speed / RPM with glowing gradient sweep and digital readouts.
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

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(240, 240)

    def set_value(self, value: float, sub_val: str = "") -> None:
        self.current_val = max(self.min_val, min(self.max_val, value))
        if sub_val:
            self.sub_val = sub_val
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        side = min(width, height)
        center_x = width / 2.0
        center_y = height / 2.0

        # Gauge dimensions
        radius = (side / 2.0) - 20.0
        rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)

        # Arc Angles (Degrees, standard Qt: 0 is 3 o'clock, CCW)
        # 225 deg span from bottom-left (225°) down to bottom-right (-45°)
        start_angle_deg = 225.0
        total_span_deg = -270.0  # Clockwise 270 degrees sweep

        # 1. Background Arc Track
        pen_bg = QPen(COLOR_GAUGE_TRACK, 16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, int(start_angle_deg * 16), int(total_span_deg * 16))

        # 2. Active Value Arc with Dynamic Color Gradient
        fraction = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        active_span_deg = total_span_deg * fraction

        if fraction > 0.005:
            # Choose color based on value intensity
            if fraction < 0.6:
                arc_color = COLOR_CYAN
            elif fraction < 0.85:
                arc_color = COLOR_BLUE
            else:
                arc_color = COLOR_AMBER

            pen_active = QPen(arc_color, 16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_active)
            painter.drawArc(rect, int(start_angle_deg * 16), int(active_span_deg * 16))

        # 3. Subtle Inner Accent Ring
        inner_rect = QRectF(center_x - radius + 14, center_y - radius + 14, (radius - 14) * 2, (radius - 14) * 2)
        pen_inner = QPen(QColor(30, 41, 59, 120), 2)
        painter.setPen(pen_inner)
        painter.drawArc(inner_rect, int(start_angle_deg * 16), int(total_span_deg * 16))

        # 4. Large Digital Speed Readout
        painter.setPen(COLOR_TEXT_PRIMARY)
        font_val = QFont("Segoe UI", int(side * 0.22), QFont.Weight.Bold)
        painter.setFont(font_val)

        val_str = f"{int(round(self.current_val))}"
        val_rect = QRectF(center_x - radius, center_y - radius * 0.45, radius * 2, radius * 0.7)
        painter.drawText(val_rect, Qt.AlignmentFlag.AlignCenter, val_str)

        # 5. Unit Label
        painter.setPen(COLOR_CYAN)
        font_unit = QFont("Segoe UI", int(side * 0.055), QFont.Weight.DemiBold)
        painter.setFont(font_unit)
        unit_rect = QRectF(center_x - radius, center_y + radius * 0.15, radius * 2, radius * 0.3)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, self.unit)

        # 6. Secondary Metric (e.g. RPM)
        painter.setPen(COLOR_TEXT_MUTED)
        font_sub = QFont("Consolas", int(side * 0.045), QFont.Weight.Normal)
        painter.setFont(font_sub)
        sub_rect = QRectF(center_x - radius, center_y + radius * 0.42, radius * 2, radius * 0.25)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, f"{self.sub_val_label}: {self.sub_val}")

        painter.end()


class PowerBarWidget(QWidget):
    """
    Bidirectional center-zero Power / Regenerative Braking Meter.
    Left (<0 kW): Green Regen | Right (>0 kW): Electric Blue / Orange Discharge.
    """

    def __init__(self, max_kw: float = 120.0, max_regen_kw: float = 60.0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.max_kw = max_kw
        self.max_regen_kw = max_regen_kw
        self.power_kw = 0.0
        self.setMinimumHeight(44)

    def set_power(self, power_kw: float) -> None:
        self.power_kw = power_kw
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_height = 14.0
        y = (h - bar_height) / 2.0

        # Background track
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, y, w, bar_height), 7, 7)

        # Center line
        center_x = w * (self.max_regen_kw / (self.max_kw + self.max_regen_kw))
        painter.setPen(QPen(QColor("#475569"), 2))
        painter.drawLine(int(center_x), int(y - 3), int(center_x), int(y + bar_height + 3))

        # Active Fill
        if self.power_kw < 0:
            # Regen (leftwards from center)
            ratio = min(1.0, abs(self.power_kw) / self.max_regen_kw)
            fill_w = center_x * ratio
            fill_rect = QRectF(center_x - fill_w, y, fill_w, bar_height)
            painter.setBrush(QBrush(COLOR_GREEN))
            painter.drawRoundedRect(fill_rect, 6, 6)
        elif self.power_kw > 0:
            # Discharge (rightwards from center)
            ratio = min(1.0, self.power_kw / self.max_kw)
            fill_w = (w - center_x) * ratio
            fill_rect = QRectF(center_x, y, fill_w, bar_height)
            color = COLOR_AMBER if self.power_kw > (self.max_kw * 0.75) else COLOR_BLUE
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(fill_rect, 6, 6)

        painter.end()


class BatteryStatusWidget(QWidget):
    """
    Renders high-visibility Battery SoC gauge, pack voltage, and estimated range.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.soc = 100.0
        self.voltage = 400.0
        self.current = 0.0
        self.est_range_km = 340.0
        self.setMinimumSize(180, 160)

    def set_battery_data(self, soc: float, voltage: float, current: float) -> None:
        self.soc = max(0.0, min(100.0, soc))
        self.voltage = voltage
        self.current = current
        # Approx 4.2 km per % SoC
        self.est_range_km = self.soc * 4.2
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Determine battery color
        if self.soc > 30.0:
            bar_color = COLOR_GREEN
        elif self.soc > 15.0:
            bar_color = COLOR_AMBER
        else:
            bar_color = COLOR_RED

        # 1. Large SoC Percentage
        painter.setPen(COLOR_TEXT_PRIMARY)
        font_soc = QFont("Segoe UI", 28, QFont.Weight.Bold)
        painter.setFont(font_soc)
        painter.drawText(QRectF(0, 0, w, 40), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{self.soc:.1f}%")

        # 2. Battery Bar Shell
        bar_y = 48.0
        bar_h = 20.0
        bar_w = w - 12.0

        # Main body
        painter.setBrush(QBrush(COLOR_GAUGE_TRACK))
        painter.setPen(QPen(COLOR_CARD_BORDER, 2))
        painter.drawRoundedRect(QRectF(0, bar_y, bar_w, bar_h), 5, 5)

        # Battery terminal nipple
        painter.setBrush(QBrush(COLOR_CARD_BORDER))
        painter.drawRoundedRect(QRectF(bar_w, bar_y + 4, 6, bar_h - 8), 2, 2)

        # Active Fill Segments
        inner_fill_w = max(0.0, (bar_w - 6) * (self.soc / 100.0))
        if inner_fill_w > 0:
            painter.setBrush(QBrush(bar_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(3, bar_y + 3, inner_fill_w, bar_h - 6), 3, 3)

        # 3. Voltage and Range metrics
        painter.setPen(COLOR_TEXT_MUTED)
        font_label = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        painter.setFont(font_label)

        painter.drawText(QRectF(0, 80, w / 2, 20), Qt.AlignmentFlag.AlignLeft, "PACK VOLTAGE")
        painter.drawText(QRectF(w / 2, 80, w / 2, 20), Qt.AlignmentFlag.AlignRight, "EST. RANGE")

        painter.setPen(COLOR_TEXT_PRIMARY)
        font_data = QFont("Consolas", 13, QFont.Weight.Bold)
        painter.setFont(font_data)

        painter.drawText(QRectF(0, 102, w / 2, 22), Qt.AlignmentFlag.AlignLeft, f"{self.voltage:.1f} V")
        painter.drawText(QRectF(w / 2, 102, w / 2, 22), Qt.AlignmentFlag.AlignRight, f"{int(self.est_range_km)} km")

        painter.end()


class LiveSparklineWidget(QWidget):
    """
    Rolling real-time telemetry sparkline graph for speed and power.
    """

    def __init__(self, max_points: int = 50, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.max_points = max_points
        self.speed_history: Deque[float] = deque(maxlen=max_points)
        self.power_history: Deque[float] = deque(maxlen=max_points)
        self.setMinimumHeight(70)

        # Initialize with zeroes
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

        # Background grid / frame
        painter.setBrush(QBrush(QColor("#0d121c")))
        painter.setPen(QPen(COLOR_CARD_BORDER, 1))
        painter.drawRoundedRect(QRectF(0, 0, w - 1, h - 1), 6, 6)

        # Grid guidelines
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, int(h * 0.25), w, int(h * 0.25))
        painter.drawLine(0, int(h * 0.5), w, int(h * 0.5))
        painter.drawLine(0, int(h * 0.75), w, int(h * 0.75))

        count = len(self.speed_history)
        if count < 2:
            painter.end()
            return

        step_x = w / (self.max_points - 1)

        # 1. Speed Path (Cyan)
        max_speed = 180.0
        speed_path = QPainterPath()
        for i, val in enumerate(self.speed_history):
            clamped = max(0.0, min(max_speed, val))
            y = h - (clamped / max_speed) * (h - 10) - 5
            x = i * step_x
            if i == 0:
                speed_path.moveTo(x, y)
            else:
                speed_path.lineTo(x, y)

        painter.setPen(QPen(COLOR_CYAN, 2))
        painter.drawPath(speed_path)

        # 2. Power Path (Electric Blue / Lime)
        power_path = QPainterPath()
        max_power = 120.0
        for i, val in enumerate(self.power_history):
            clamped = max(-40.0, min(max_power, val))
            y = h - ((clamped + 40.0) / (max_power + 40.0)) * (h - 10) - 5
            x = i * step_x
            if i == 0:
                power_path.moveTo(x, y)
            else:
                power_path.lineTo(x, y)

        painter.setPen(QPen(COLOR_AMBER, 1.5, Qt.PenStyle.DotLine))
        painter.drawPath(power_path)

        # Legend
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(COLOR_CYAN)
        painter.drawText(10, 14, "— SPEED")
        painter.setPen(COLOR_AMBER)
        painter.drawText(75, 14, "… POWER")

        painter.end()


class ThermalMonitorWidget(QWidget):
    """
    Displays thermal status of Powertrain components (Motor, Inverter, Battery).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.motor_temp = 0.0
        self.inverter_temp = 0.0
        self.batt_temp = 0.0

    def set_temperatures(self, motor: float, inverter: float, battery: float) -> None:
        self.motor_temp = motor
        self.inverter_temp = inverter
        self.batt_temp = battery
        self.update()

    def _temp_color(self, temp: float, warn_thresh: float, crit_thresh: float) -> QColor:
        if temp >= crit_thresh:
            return COLOR_RED
        elif temp >= warn_thresh:
            return COLOR_AMBER
        return COLOR_GREEN

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        items = [
            ("MOTOR", self.motor_temp, 75.0, 90.0),
            ("INVERTER", self.inverter_temp, 65.0, 80.0),
            ("BATTERY", self.batt_temp, 42.0, 50.0),
        ]

        col_w = w / len(items)

        for i, (label, temp, warn_th, crit_th) in enumerate(items):
            box_rect = QRectF(i * col_w + 4, 0, col_w - 8, self.height())
            color = self._temp_color(temp, warn_th, crit_th)

            painter.setPen(COLOR_TEXT_MUTED)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(
                QRectF(box_rect.x(), 2, box_rect.width(), 16),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

            painter.setPen(color)
            painter.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
            painter.drawText(
                QRectF(box_rect.x(), 20, box_rect.width(), 22),
                Qt.AlignmentFlag.AlignCenter,
                f"{temp:.1f}°C",
            )

        painter.end()


class VoltesseDashboard(QMainWindow):
    """
    Main Digital Cockpit Instrument Cluster Window.
    Operates distraction-free with zero required touch inputs.
    """

    # Signals for keyboard controls (bench testing)
    drive_mode_requested = pyqtSignal()
    pause_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voltesse Dash - Digital Cockpit")
        self.setMinimumSize(1024, 600)
        self.resize(1280, 720)

        # Style sheet
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: #080B10;
            }}
            QFrame.card {{
                background-color: #111622;
                border: 1px solid #1E293B;
                border-radius: 12px;
            }}
            QLabel {{
                color: #F8FAFC;
            }}
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
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. TOP STATUS / HEADER BAR
        # -------------------------------------------------------------
        header_frame = QFrame()
        header_frame.setFixedHeight(44)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 0, 10, 0)

        # Brand / Title
        brand_label = QLabel("⚡ VOLTESSE")
        brand_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Black))
        brand_label.setStyleSheet("color: #00E5FF; letter-spacing: 2px;")

        dash_subtitle = QLabel("DASH EMBEDDED CLUSTER")
        dash_subtitle.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        dash_subtitle.setStyleSheet("color: #64748B; margin-left: 6px;")

        # Active Drive Mode Pill
        self.mode_badge = QLabel("DRIVE")
        self.mode_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.mode_badge.setStyleSheet(
            """
            background-color: #1E3A8A;
            color: #60A5FA;
            padding: 4px 14px;
            border-radius: 8px;
            font-weight: bold;
            """
        )

        # Status / Warning Pill
        self.status_badge = QLabel("SYSTEM READY")
        self.status_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.status_badge.setStyleSheet(
            """
            background-color: #064E3B;
            color: #34D399;
            padding: 4px 14px;
            border-radius: 8px;
            """
        )

        # Live Clock
        self.clock_label = QLabel("00:00:00")
        self.clock_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.clock_label.setStyleSheet("color: #F8FAFC;")

        header_layout.addWidget(brand_label)
        header_layout.addWidget(dash_subtitle)
        header_layout.addStretch(1)
        header_layout.addWidget(self.mode_badge)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.status_badge)
        header_layout.addSpacing(20)
        header_layout.addWidget(self.clock_label)

        main_layout.addWidget(header_frame)

        # -------------------------------------------------------------
        # 2. MAIN COCKPIT DASHBOARD GRID
        # -------------------------------------------------------------
        cockpit_grid = QGridLayout()
        cockpit_grid.setSpacing(14)

        # --- LEFT PANEL: Battery, Energy & Range ---
        left_card = QFrame()
        left_card.setProperty("class", "card")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)

        left_title = QLabel("ENERGY & STORAGE")
        left_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        left_title.setStyleSheet("color: #00E5FF;")
        left_layout.addWidget(left_title)

        self.battery_widget = BatteryStatusWidget()
        left_layout.addWidget(self.battery_widget)

        # Current Amperage Readout
        amp_box = QHBoxLayout()
        amp_lbl = QLabel("CURRENT DRAW:")
        amp_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        amp_lbl.setStyleSheet("color: #64748B;")
        self.amp_val = QLabel("0.0 A")
        self.amp_val.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.amp_val.setStyleSheet("color: #F8FAFC;")
        amp_box.addWidget(amp_lbl)
        amp_box.addStretch(1)
        amp_box.addWidget(self.amp_val)
        left_layout.addLayout(amp_box)

        cockpit_grid.addWidget(left_card, 0, 0, 1, 1)

        # --- CENTER PANEL: Primary Speedometer Gauge ---
        center_card = QFrame()
        center_card.setProperty("class", "card")
        center_layout = QVBoxLayout(center_card)
        center_layout.setContentsMargins(10, 10, 10, 10)

        self.speed_gauge = ArcGaugeWidget(min_val=0.0, max_val=180.0, title="SPEED", unit="KM/H")
        center_layout.addWidget(self.speed_gauge)

        cockpit_grid.addWidget(center_card, 0, 1, 1, 1)

        # --- RIGHT PANEL: Power Meter & Throttle/Brake Dynamics ---
        right_card = QFrame()
        right_card.setProperty("class", "card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        right_title = QLabel("POWERTRAIN DYNAMICS")
        right_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        right_title.setStyleSheet("color: #00E5FF;")
        right_layout.addWidget(right_title)

        # Power Delivery Readout
        power_num_box = QHBoxLayout()
        self.power_label = QLabel("NET POWER:")
        self.power_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.power_label.setStyleSheet("color: #64748B;")
        self.power_val = QLabel("0.0 kW")
        self.power_val.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        self.power_val.setStyleSheet("color: #00E5FF;")
        power_num_box.addWidget(self.power_label)
        power_num_box.addStretch(1)
        power_num_box.addWidget(self.power_val)
        right_layout.addLayout(power_num_box)

        # Power / Regen Bar
        self.power_bar = PowerBarWidget()
        right_layout.addWidget(self.power_bar)

        # Throttle & Brake indicators
        pedal_box = QHBoxLayout()
        self.throttle_label = QLabel("THR: 0%")
        self.throttle_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.throttle_label.setStyleSheet("color: #38BDF8;")
        self.brake_label = QLabel("BRK: 0%")
        self.brake_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.brake_label.setStyleSheet("color: #F43F5E;")
        pedal_box.addWidget(self.throttle_label)
        pedal_box.addStretch(1)
        pedal_box.addWidget(self.brake_label)
        right_layout.addLayout(pedal_box)

        right_layout.addStretch(1)
        cockpit_grid.addWidget(right_card, 0, 2, 1, 1)

        # Set column stretch factors for optimal aspect ratio (1 : 1.3 : 1)
        cockpit_grid.setColumnStretch(0, 3)
        cockpit_grid.setColumnStretch(1, 4)
        cockpit_grid.setColumnStretch(2, 3)

        main_layout.addLayout(cockpit_grid, stretch=3)

        # -------------------------------------------------------------
        # 3. BOTTOM PANEL: Diagnostics, Telemetry Trace & Trip Stats
        # -------------------------------------------------------------
        bottom_card = QFrame()
        bottom_card.setProperty("class", "card")
        bottom_layout = QHBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.setSpacing(20)

        # Trip Stats Column
        trip_col = QVBoxLayout()
        trip_title = QLabel("TRIP STATS")
        trip_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        trip_title.setStyleSheet("color: #64748B;")
        trip_col.addWidget(trip_title)

        self.trip_dist_val = QLabel("0.00 km")
        self.trip_dist_val.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.trip_dist_val.setStyleSheet("color: #F8FAFC;")
        trip_col.addWidget(self.trip_dist_val)
        bottom_layout.addLayout(trip_col, stretch=1)

        # Thermal Diagnostics Column
        thermal_col = QVBoxLayout()
        thermal_title = QLabel("THERMAL MANAGEMENT")
        thermal_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        thermal_title.setStyleSheet("color: #64748B;")
        thermal_col.addWidget(thermal_title)

        self.thermal_widget = ThermalMonitorWidget()
        self.thermal_widget.setFixedHeight(46)
        thermal_col.addWidget(self.thermal_widget)
        bottom_layout.addLayout(thermal_col, stretch=2)

        # Rolling Realtime Telemetry Sparkline
        sparkline_col = QVBoxLayout()
        spark_title = QLabel("REAL-TIME TELEMETRY TRACE")
        spark_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        spark_title.setStyleSheet("color: #64748B;")
        sparkline_col.addWidget(spark_title)

        self.sparkline_widget = LiveSparklineWidget(max_points=60)
        self.sparkline_widget.setFixedHeight(50)
        sparkline_col.addWidget(self.sparkline_widget)
        bottom_layout.addLayout(sparkline_col, stretch=3)

        main_layout.addWidget(bottom_card, stretch=1)

    def _update_clock(self) -> None:
        self.clock_label.setText(time.strftime("%H:%M:%S"))

    def update_telemetry(self, record: TelemetryRecord) -> None:
        """
        Receives and renders a new telemetry frame onto the cockpit cluster.
        Non-blocking slot connected to background telemetry stream.
        """
        # Speedometer & RPM
        self.speed_gauge.set_value(record.speed_kmh, sub_val=str(record.motor_rpm))

        # Battery & Voltage
        self.battery_widget.set_battery_data(
            record.battery_soc, record.battery_voltage, record.battery_current
        )
        self.amp_val.setText(f"{record.battery_current:+.1f} A")

        # Power & Regen
        self.power_val.setText(f"{record.battery_power_kw:+.1f} kW")
        if record.battery_power_kw < -0.5:
            self.power_val.setStyleSheet("color: #00E676;")  # Green for Regen
        elif record.battery_power_kw > 60.0:
            self.power_val.setStyleSheet("color: #FFAB00;")  # Amber for High Load
        else:
            self.power_val.setStyleSheet("color: #00E5FF;")  # Cyan for Normal

        self.power_bar.set_power(record.battery_power_kw)

        # Pedals
        self.throttle_label.setText(f"THR: {int(record.throttle_pct)}%")
        self.brake_label.setText(f"BRK: {int(record.brake_pct)}%")

        # Drive Mode badge
        self.mode_badge.setText(record.drive_mode)
        if record.drive_mode == "SPORT":
            self.mode_badge.setStyleSheet(
                "background-color: #881337; color: #FB7185; padding: 4px 14px; border-radius: 8px; font-weight: bold;"
            )
        elif record.drive_mode == "ECO":
            self.mode_badge.setStyleSheet(
                "background-color: #064E3B; color: #34D399; padding: 4px 14px; border-radius: 8px; font-weight: bold;"
            )
        else:
            self.mode_badge.setStyleSheet(
                "background-color: #1E3A8A; color: #60A5FA; padding: 4px 14px; border-radius: 8px; font-weight: bold;"
            )

        # Warnings / Status
        if record.warnings:
            warn_text = " | ".join(record.warnings)
            self.status_badge.setText(f"⚠ {warn_text}")
            self.status_badge.setStyleSheet(
                "background-color: #7F1D1D; color: #FCA5A5; padding: 4px 14px; border-radius: 8px; font-weight: bold;"
            )
        else:
            self.status_badge.setText("SYSTEM READY")
            self.status_badge.setStyleSheet(
                "background-color: #064E3B; color: #34D399; padding: 4px 14px; border-radius: 8px;"
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
        """Convenient keyboard controls for testing on development machines."""
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
