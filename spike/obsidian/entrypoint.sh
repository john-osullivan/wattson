#!/bin/bash
set -euo pipefail

VAULT_DIR="${WATTSON_VAULT_DIR:-/data/vault}"
mkdir -p "$VAULT_DIR" /data/state

# 1. virtual display (clean stale state: /tmp persists across container restarts)
pkill -x Xvfb 2>/dev/null || true
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
for _ in $(seq 1 50); do
  [ -e /tmp/.X11-unix/X99 ] && break
  sleep 0.2
done
export DISPLAY=:99

# 2. VNC + browser view (noVNC behind nginx; nginx strips the pod preview prefix)
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 >/data/state/x11vnc.log 2>&1 &
websockify --web /usr/share/novnc/ 127.0.0.1:6081 127.0.0.1:5900 >/data/state/websockify.log 2>&1 &
cat > /etc/nginx/sites-available/default <<'EOF'
server {
    listen 6080;
    location /__preview/6080/ {
        proxy_pass http://127.0.0.1:6081/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
    location / {
        proxy_pass http://127.0.0.1:6081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }
}
EOF
nginx
echo "[entrypoint] noVNC on :6080 (nginx -> websockify :6081), VNC on :5900"

# 3. Obsidian (Electron needs --no-sandbox when running as root)
exec obsidian --no-sandbox --disable-gpu --disable-dev-shm-usage "$VAULT_DIR"
