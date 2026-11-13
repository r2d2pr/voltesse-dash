# Voltesse Dash Systemd Services

Systemd service unit definitions for running the Voltesse Cockpit and Technician Web Portal on embedded displays (e.g. Raspberry Pi) on startup.

## Files
- `voltesse-dash.service`: Runs the PyQt6 driver cockpit in kiosk mode using the `cage` Wayland kiosk compositor.
- `voltesse-figma-gui.service`: Runs the React + FastAPI technician web portal on port 8501 with real-time 20 Hz push stream.

## Installation on Raspberry Pi

```bash
# 1. Copy service files to systemd directory
sudo cp services/voltesse-dash.service /etc/systemd/system/
sudo cp services/voltesse-figma-gui.service /etc/systemd/system/

# 2. Reload systemd daemon
sudo systemctl daemon-reload

# 3. Enable services to launch on boot
sudo systemctl enable voltesse-dash.service
sudo systemctl enable voltesse-figma-gui.service

# 4. Restart or start immediately
sudo systemctl restart voltesse-dash.service
sudo systemctl restart voltesse-figma-gui.service
```

## Monitoring Logs

```bash
# Cockpit logs
journalctl -u voltesse-dash.service -f

# Technician Portal logs (FastAPI/React GUI)
journalctl -u voltesse-figma-gui.service -f
```
