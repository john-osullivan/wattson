#!/bin/bash
set -euo pipefail

VAULT_DIR="${WATTSON_VAULT_DIR:-/data/vault}"
mkdir -p "$VAULT_DIR" /data/state

# 1. virtual display
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
for _ in $(seq 1 50); do
  [ -e /tmp/.X11-unix/X99 ] && break
  sleep 0.2
done
export DISPLAY=:99

# 2. VNC + browser view (noVNC)
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 >/data/state/x11vnc.log 2>&1 &
websockify --web /usr/share/novnc/ 0.0.0.0:6080 127.0.0.1:5900 >/data/state/websockify.log 2>&1 &
echo "[entrypoint] noVNC on :6080 (vnc.html), VNC on :5900"

# 3. Obsidian (Electron needs --no-sandbox when running as root)
exec obsidian --no-sandbox --disable-gpu --disable-dev-shm-usage "$VAULT_DIR"
