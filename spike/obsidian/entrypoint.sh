#!/bin/bash
set -euo pipefail

VAULT_DIR="${WATTSON_VAULT_DIR:-/data/vault}"
PROFILE_DIR="/home/ubuntu/.config/obsidian"
mkdir -p "$VAULT_DIR" /data/state "$PROFILE_DIR"

# Volumes may hold root-owned files from earlier image builds; make everything
# writable by uid 1000 so host and container share ownership of the vault.
chown -R 1000:1000 "$VAULT_DIR" /data/state "$PROFILE_DIR"
chown -R 1000:1000 /var/log/nginx /var/lib/nginx
sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf

# 1. virtual display (clean stale state: /tmp persists across container restarts)
pkill -x Xvfb 2>/dev/null || true
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

# 2. noVNC web assets (generated as root; world-readable for websockify)
echo '{"name":"noVNC","version":"1.3.0"}' > /usr/share/novnc/package.json
cat > /usr/share/novnc/wattson-vnc.html <<'EOF'
<!doctype html><html><head><meta charset="utf-8"><title>WATTSON VNC</title></head>
<body>Redirecting to noVNC…<script>
var dir = location.pathname.replace(/\/[^\/]*$/, '/');
var path = dir.replace(/^\//, '') + 'websockify';
location.replace('vnc.html?path=' + encodeURIComponent(path) + '&autoconnect=true');
</script></body></html>
EOF

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

# 3. all services as uid 1000 (nginx pid to /tmp since /run is root-owned)
exec runuser -u ubuntu -- bash -c '
  Xvfb :99 -screen 0 1280x720x24 -nolisten tcp &
  for _ in $(seq 1 50); do
    [ -e /tmp/.X11-unix/X99 ] && break
    sleep 0.2
  done
  export DISPLAY=:99
  x11vnc -display :99 -forever -shared -nopw -rfbport 5900 >/data/state/x11vnc.log 2>&1 &
  websockify --web /usr/share/novnc/ 127.0.0.1:6081 127.0.0.1:5900 >/data/state/websockify.log 2>&1 &
  nginx
  echo "[entrypoint] noVNC on :6080 (nginx -> websockify :6081), VNC on :5900"
  while true; do
    obsidian --no-sandbox --disable-gpu --disable-dev-shm-usage '"$VAULT_DIR"' || true
    echo "[entrypoint] obsidian exited; restarting in 2s" >&2
    sleep 2
  done
'
