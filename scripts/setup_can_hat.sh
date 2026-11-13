#!/bin/bash
# ==============================================================================
# Voltesse Dash - Waveshare RS485 CAN HAT Hardware Setup Script
# Configures MCP2515 SPI overlay, 12MHz oscillator, GPIO 25 interrupt,
# installs can-utils, and provisions automatic 500k baud SocketCAN bring-up.
# ==============================================================================

set -euo pipefail

echo "==================================================================="
echo "  Voltesse Dash - Waveshare RS485 CAN HAT Automated Configuration  "
echo "==================================================================="

# 1. Require root privileges
if [ "$EUID" -ne 0 ]; then
  echo "[-] ERROR: This script must be run as root (use sudo)." >&2
  exit 1
fi

# 2. Locate Raspberry Pi boot configuration file
CONFIG_TXT=""
if [ -f "/boot/firmware/config.txt" ]; then
  CONFIG_TXT="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
  CONFIG_TXT="/boot/config.txt"
else
  echo "[-] ERROR: Could not locate config.txt in /boot/firmware/ or /boot/." >&2
  exit 1
fi
echo "[+] Detected boot config: ${CONFIG_TXT}"

# Backup config.txt before modifications
BACKUP_PATH="${CONFIG_TXT}.bak.$(date +%Y%m%d%H%M%S)"
cp "${CONFIG_TXT}" "${BACKUP_PATH}"
echo "[+] Created backup at: ${BACKUP_PATH}"

# 3. Enable SPI bus
if grep -q "^#dtparam=spi=on" "${CONFIG_TXT}"; then
  sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' "${CONFIG_TXT}"
  echo "[+] Uncommented dtparam=spi=on"
elif ! grep -q "^dtparam=spi=on" "${CONFIG_TXT}"; then
  echo "dtparam=spi=on" >> "${CONFIG_TXT}"
  echo "[+] Appended dtparam=spi=on"
else
  echo "[*] SPI is already enabled (dtparam=spi=on)"
fi

# 4. Configure MCP2515 Device Tree Overlay (12 MHz oscillator, GPIO 25 interrupt)
OVERLAY_LINE="dtoverlay=mcp2515-can0,oscillator=12000000,interrupt=25"
if grep -q "^dtoverlay=mcp2515-can0" "${CONFIG_TXT}"; then
  sed -i "s|^dtoverlay=mcp2515-can0.*|${OVERLAY_LINE}|" "${CONFIG_TXT}"
  echo "[+] Updated existing mcp2515-can0 dtoverlay entry"
else
  echo "${OVERLAY_LINE}" >> "${CONFIG_TXT}"
  echo "[+] Appended: ${OVERLAY_LINE}"
fi

# 5. Install can-utils if not installed
if ! command -v candump &> /dev/null; then
  echo "[+] Installing can-utils package..."
  apt-get update -qq
  apt-get install -y --no-install-recommends can-utils
fi
echo "[+] can-utils is ready."

# 6. Configure persistent SocketCAN can0 systemd service (500,000 baud, txqueuelen 1000)
SERVICE_PATH="/etc/systemd/system/voltesse-can0.service"
cat << 'EOF' > "${SERVICE_PATH}"
[Unit]
Description=Voltesse Dash - SocketCAN can0 Automatic Bring-Up
Documentation=https://github.com/david/voltesse-dash
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=-/sbin/ip link set can0 down
ExecStart=/sbin/ip link set can0 up type can bitrate 500000
ExecStartPost=/sbin/ip link set can0 txqueuelen 1000
ExecStop=/sbin/ip link set can0 down

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "${SERVICE_PATH}"
systemctl daemon-reload
systemctl enable voltesse-can0.service
echo "[+] Enabled persistent voltesse-can0.service at 500,000 baud (500k)"

echo "==================================================================="
echo "  [SUCCESS] Waveshare RS485 CAN HAT configured successfully!      "
echo "  Reboot the Raspberry Pi to initialize the SPI overlay:           "
echo "    sudo reboot                                                    "
echo "  Verify after reboot:                                             "
echo "    ip -details link show can0                                     "
echo "    candump can0                                                   "
echo "==================================================================="
