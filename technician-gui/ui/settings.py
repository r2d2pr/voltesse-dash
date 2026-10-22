"""
Adjustable warning thresholds and PostgreSQL database connection management.
Exclusively standardized on Imperial units (°F) with Voltesse cyber styling.
"""

import streamlit as st

from data.db import get_db_url, test_connection


def show_settings():
    st.markdown(
        """
        <div style="margin-bottom: 12px;">
            <h2 style="margin: 0; padding: 0; font-weight: 800; letter-spacing: 0.05em; color: #FFFFFF;">
                ⚙️ SYSTEM & TELEMETRY SETTINGS
            </h2>
            <p style="margin: 0; padding: 0; font-size: 0.82rem; color: #94A3B8;">
                Configure telemetry alert limits, database connectivity, and technician calibration parameters.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("PostgreSQL Persistence Engine")
    is_connected, msg = test_connection()
    c1, c2 = st.columns([3, 1])
    c1.text_input("Database URL (VOLTESSE_DB_URL)", value=get_db_url(), disabled=True)
    if c2.button("Test Connection", width="stretch"):
        st.rerun()

    if is_connected:
        st.markdown(
            f"""
            <div style="background: rgba(0, 245, 212, 0.08); border: 1px solid rgba(0, 245, 212, 0.4); 
                        border-radius: 6px; padding: 8px 14px; margin-bottom: 14px;">
                <span class="v-pill v-pill-active">🟢 POSTGRESQL 16 CONNECTED</span>
                <span style="margin-left: 10px; font-size: 0.85rem; color: #E2E8F0;">{msg}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background: rgba(255, 184, 0, 0.08); border: 1px solid rgba(255, 184, 0, 0.4); 
                        border-radius: 6px; padding: 8px 14px; margin-bottom: 14px;">
                <span class="v-pill v-pill-standby">🟡 DATABASE STANDBY</span>
                <span style="margin-left: 10px; font-size: 0.85rem; color: #E2E8F0;">{msg}</span>
                <div style="margin-top: 6px; font-size: 0.78rem; color: #94A3B8;">
                    Launch local PostgreSQL container via Docker: <code>cd db && docker compose up -d</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("Telemetry Warning Thresholds (Imperial)")
    st.caption("Configure vehicle alert limits. These settings drive live warnings, notifications, and diagnostic chart thresholds.")

    st.session_state.warning_temp = st.slider(
        "Motor Temperature Warning Limit (°F)",
        min_value=110, max_value=230,
        value=st.session_state.get("warning_temp", 160), step=5,
        help="Nominal < 160°F | Warm >= 160°F | Hot >= 195°F",
    )
    st.session_state.warning_battery = st.slider(
        "Low Battery SoC Warning Limit (%)",
        min_value=5, max_value=40,
        value=st.session_state.get("warning_battery", 20), step=5,
        help="Triggers low energy alert when state-of-charge drops below this percentage.",
    )

    st.subheader("Active Calibration Summary")
    left, right = st.columns(2)
    left.metric(
        "Motor Temp Warning Limit",
        f"{st.session_state.warning_temp} °F",
        delta="Imperial Standard",
        delta_color="off",
        border=True,
    )
    right.metric(
        "Low Battery SoC Limit",
        f"{st.session_state.warning_battery}%",
        delta="Pack Threshold",
        delta_color="off",
        border=True,
    )

    render_palette_calibration()

    from ui.diagnostics import render_dtc_console
    render_dtc_console()


def render_palette_calibration():
    st.divider()
    st.subheader("🎨 Cockpit Ambient Palette Calibration (v5.4.0)")
    st.caption(
        "Bench-calibrate and preview the 5 signature OLED colorways engineered for the Voltesse cockpit instrument cluster. "
        "Select a colorway to inspect accent tokens, OLED contrast compliance, and live cluster dial styling."
    )

    palette_defs = {
        "mint": {
            "name": "CYBER_MINT",
            "display": "Cyber-Mint",
            "primary": "#00F5A0",
            "highlight": "#5CFFC7",
            "secondary": "#00E5FF",
            "dim": "rgba(0, 245, 160, 0.15)",
            "vibe": "Voltesse signature cybernetic electric neon",
            "contrast_ratio": "14.2:1 (OLED AAA)",
            "compliance": "PASS • ISO/SAE Invariant",
        },
        "stealth": {
            "name": "STEALTH_MONOCHROME",
            "display": "Stealth Monochrome",
            "primary": "#E2E8F0",
            "highlight": "#FFFFFF",
            "secondary": "#94A3B8",
            "dim": "rgba(226, 232, 240, 0.15)",
            "vibe": "Pure hypercar titanium silver & white",
            "contrast_ratio": "15.8:1 (OLED AAA)",
            "compliance": "PASS • ISO/SAE Invariant",
        },
        "amber": {
            "name": "SOLAR_AMBER",
            "display": "Solar Amber",
            "primary": "#FFB800",
            "highlight": "#FFD166",
            "secondary": "#FF9F1C",
            "dim": "rgba(255, 184, 0, 0.15)",
            "vibe": "Endurance motorsport amber tachometer",
            "contrast_ratio": "11.6:1 (OLED AAA)",
            "compliance": "PASS • ISO/SAE Invariant",
        },
        "redline": {
            "name": "TRACK_REDLINE",
            "display": "Track Redline",
            "primary": "#FF3366",
            "highlight": "#FF6B8B",
            "secondary": "#FF9900",
            "dim": "rgba(255, 51, 102, 0.15)",
            "vibe": "Aggressive track attack crimson",
            "contrast_ratio": "7.9:1 (OLED AA)",
            "compliance": "PASS • ISO/SAE Invariant",
        },
        "synthwave": {
            "name": "NEON_SYNTHWAVE",
            "display": "Neon Synthwave",
            "primary": "#D946EF",
            "highlight": "#F472B6",
            "secondary": "#06B6D4",
            "dim": "rgba(217, 70, 239, 0.15)",
            "vibe": "Cyberpunk night drive magenta & cyan",
            "contrast_ratio": "9.4:1 (OLED AAA)",
            "compliance": "PASS • ISO/SAE Invariant",
        },
    }

    if "calib_palette" not in st.session_state:
        st.session_state.calib_palette = "mint"

    cols = st.columns(5)
    for idx, (pkey, pval) in enumerate(palette_defs.items()):
        is_sel = (st.session_state.calib_palette == pkey)
        border_col = pval["primary"] if is_sel else "rgba(255, 255, 255, 0.12)"
        glow = f"box-shadow: 0 0 12px {pval['primary']}40;" if is_sel else ""
        badge = "✓ ACTIVE" if is_sel else "SELECT"
        with cols[idx]:
            st.markdown(
                f"""
                <div style="background: rgba(8, 12, 14, 0.95); border: 2px solid {border_col}; {glow} 
                            border-radius: 8px; padding: 10px 8px; text-align: center; margin-bottom: 6px;">
                    <div style="width: 100%; height: 20px; background: linear-gradient(90deg, {pval['primary']}, {pval['highlight']}, {pval['secondary']}); border-radius: 4px; margin-bottom: 6px;"></div>
                    <div style="font-size: 0.78rem; font-weight: 700; color: #FFFFFF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{pval['display']}</div>
                    <div style="font-size: 0.68rem; color: #94A3B8; font-family: Consolas, monospace;">{pval['primary']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(badge, key=f"btn_pal_{pkey}", use_container_width=True):
                st.session_state.calib_palette = pkey
                st.rerun()

    active_p = palette_defs[st.session_state.calib_palette]

    # Metric breakdown cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Colorway", active_p["display"], delta=active_p["name"], border=True)
    m2.metric("Primary Accent", active_p["primary"], delta="Bezels & Needles", delta_color="off", border=True)
    m3.metric("Highlight Glow", active_p["highlight"], delta="Readouts & Badges", delta_color="off", border=True)
    m4.metric("OLED Contrast", active_p["contrast_ratio"], delta=active_p["compliance"], border=True)

    # SVG & CSS High-Fidelity Cluster Dial Preview
    p_pri = active_p["primary"]
    p_hl = active_p["highlight"]
    p_sec = active_p["secondary"]
    p_dim = active_p["dim"]

    st.markdown(
        f"""
        <div style="background: #000000; border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 18px; margin-top: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 0.8rem; font-weight: 700; color: #94A3B8; letter-spacing: 0.08em;">
                    CLUSTER OLED SIMULATION PREVIEW — {active_p['name']}
                </span>
                <span style="background: rgba(255,255,255,0.08); color: {p_pri}; font-size: 0.72rem; font-family: monospace; padding: 2px 8px; border-radius: 4px; border: 1px solid {p_pri}60;">
                    HOTKEY [P] AUTO-CYCLE
                </span>
            </div>
            <div style="display: flex; justify-content: space-around; align-items: center; gap: 12px; flex-wrap: wrap;">
                <!-- Left Pod: Tachometer -->
                <div style="flex: 1; min-width: 140px; max-width: 180px; text-align: center; background: rgba(12,18,22,0.6); border-radius: 8px; padding: 12px; border: 1px solid rgba(255,255,255,0.08);">
                    <svg viewBox="0 0 100 100" style="width: 100px; height: 100px; margin: 0 auto; display: block;">
                        <!-- Track -->
                        <path d="M 20 80 A 42 42 0 1 1 80 80" fill="none" stroke="#1A242B" stroke-width="6" stroke-linecap="round"/>
                        <!-- Active Arc -->
                        <path d="M 20 80 A 42 42 0 0 1 65 24" fill="none" stroke="{p_pri}" stroke-width="6" stroke-linecap="round"/>
                        <!-- Redline (Invariant Coral Red) -->
                        <path d="M 68 22 A 42 42 0 0 1 80 80" fill="none" stroke="#FF4D6D" stroke-width="6" stroke-linecap="round"/>
                        <!-- Digital Value -->
                        <text x="50" y="52" fill="#FFFFFF" font-size="14" font-weight="bold" font-family="Segoe UI" text-anchor="middle">4.2</text>
                        <text x="50" y="66" fill="{p_hl}" font-size="8" font-family="Segoe UI" text-anchor="middle">x1000 RPM</text>
                    </svg>
                    <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px;">TACHOMETER & REDLINE</div>
                </div>

                <!-- Center Pod: Speedometer -->
                <div style="flex: 1.4; min-width: 180px; max-width: 240px; text-align: center; background: rgba(12,18,22,0.8); border-radius: 8px; padding: 14px; border: 1px solid {p_pri}50; box-shadow: 0 0 15px {p_pri}25;">
                    <svg viewBox="0 0 120 120" style="width: 130px; height: 130px; margin: 0 auto; display: block;">
                        <!-- Outer Glow Ring -->
                        <circle cx="60" cy="60" r="54" fill="none" stroke="{p_dim}" stroke-width="4"/>
                        <!-- Track Ring -->
                        <circle cx="60" cy="60" r="48" fill="none" stroke="#1A242B" stroke-width="3"/>
                        <!-- Speed Grad Arc -->
                        <path d="M 22 98 A 48 48 0 1 1 98 98" fill="none" stroke="{p_pri}" stroke-width="4" stroke-dasharray="2 4"/>
                        <!-- Digital Readout -->
                        <text x="60" y="58" fill="#FFFFFF" font-size="28" font-weight="900" font-family="Segoe UI" text-anchor="middle">70</text>
                        <text x="60" y="74" fill="{p_hl}" font-size="11" font-weight="bold" font-family="Segoe UI" text-anchor="middle">MPH</text>
                        <text x="60" y="90" fill="{p_sec}" font-size="8" font-family="Consolas" text-anchor="middle">D3 • 009999 mi</text>
                    </svg>
                    <div style="font-size: 0.75rem; font-weight: 700; color: #FFFFFF; margin-top: 4px;">SPEEDOMETER CENTERPIECE</div>
                </div>

                <!-- Right Pod: Battery & SoC -->
                <div style="flex: 1; min-width: 140px; max-width: 180px; text-align: center; background: rgba(12,18,22,0.6); border-radius: 8px; padding: 12px; border: 1px solid rgba(255,255,255,0.08);">
                    <svg viewBox="0 0 100 100" style="width: 100px; height: 100px; margin: 0 auto; display: block;">
                        <!-- Track -->
                        <path d="M 20 80 A 42 42 0 1 1 80 80" fill="none" stroke="#1A242B" stroke-width="6" stroke-linecap="round"/>
                        <!-- Active SoC Arc -->
                        <path d="M 20 80 A 42 42 0 1 1 76 68" fill="none" stroke="{p_pri}" stroke-width="6" stroke-linecap="round"/>
                        <!-- Digital Value -->
                        <text x="50" y="50" fill="#FFFFFF" font-size="16" font-weight="bold" font-family="Segoe UI" text-anchor="middle">85%</text>
                        <text x="50" y="65" fill="{p_hl}" font-size="8" font-weight="bold" font-family="Segoe UI" text-anchor="middle">222 mi</text>
                    </svg>
                    <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px;">STATE OF CHARGE</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
