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

# 1. clean stale display state (TigerVNC Xvnc owns :99; /tmp persists across restarts)
pkill -x Xvnc 2>/dev/null || true
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

# 2. noVNC web assets (generated as root; world-readable for websockify)
echo '{"name":"noVNC","version":"1.3.0"}' > /usr/share/novnc/package.json
cat > /usr/share/novnc/wattson-vnc.html <<'EOF'
<!doctype html><html><head><meta charset="utf-8"><title>WATTSON VNC</title></head>
<body>Redirecting to noVNC…<script>
var dir = location.pathname.replace(/\/[^\/]*$/, '/');
var path = dir.replace(/^\//, '') + 'websockify';
location.replace('vnc.html?path=' + encodeURIComponent(path) + '&autoconnect=true&resize=remote');
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

# openbox: minimal WM config (titlebars, drag-to-move, edge-resize).
# Key syntax is "Modifier-Key" (dash-separated); Super = the Windows key
# (also "W"). Super+Up/Down toggle maximize. openbox hides decorations when
# maximized, so the kiosk view stays full-bleed until the user grabs a window edge.
mkdir -p /home/ubuntu/.config/openbox
cat > /home/ubuntu/.config/openbox/rc.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <keyboard>
    <keybind key="Super-Up">
      <action name="Maximize"/>
    </keybind>
    <keybind key="Super-Down">
      <action name="Unmaximize" direction="both"/>
    </keybind>
  </keyboard>
</openbox_config>
EOF
chown -R 1000:1000 /home/ubuntu/.config/openbox

# 3. all services as uid 1000 (nginx pid to /tmp since /run is root-owned)
exec runuser -u ubuntu -- bash -c '
  Xvnc :99 -geometry 1200x900 -depth 24 -localhost yes -rfbport 5900 \
    -SecurityTypes None -AlwaysShared >/data/state/xvnc.log 2>&1 &
  for _ in $(seq 1 50); do
    [ -e /tmp/.X11-unix/X99 ] && break
    sleep 0.2
  done
  export DISPLAY=:99
  openbox >/data/state/openbox.log 2>&1 &
  websockify --web /usr/share/novnc/ 127.0.0.1:6081 127.0.0.1:5900 >/data/state/websockify.log 2>&1 &
  nginx
  echo "[entrypoint] noVNC on :6080 (nginx -> websockify :6081), TigerVNC Xvnc on :5900"
  (
    # Keep the main Obsidian window maximized: first on appearance, then on
    # every display resize (noVNC resize=remote -> Xvnc SetDesktopSize).
    # Also restore the window if the user closed it: on Linux that only
    # tray-minimizes it (_NET_WM_STATE_HIDDEN), which is unreachable in a kiosk.
    lastgeo=""
    done_wid=""
    while true; do
      sleep 2
      geo=$(xdotool getdisplaygeometry 2>/dev/null || true)
      [ -n "$geo" ] || continue
      geo_changed=0
      if [ "$geo" != "$lastgeo" ]; then geo_changed=1; lastgeo="$geo"; fi
      wid=""
      for w in $(xdotool search --name "Obsidian" 2>/dev/null); do
        g=$(xdotool getwindowgeometry "$w" 2>/dev/null | grep Geometry | grep -oE "[0-9]+x[0-9]+" | head -1 || true)
        [ -n "$g" ] || continue
        if [ "${g%x*}" -gt 200 ] && [ "${g#*x}" -gt 200 ]; then wid="$w"; break; fi
      done
      [ -n "$wid" ] || continue
      state=$(xprop -id "$wid" _NET_WM_STATE 2>/dev/null || true)
      case "$state" in
        *HIDDEN*)
          xdotool windowmap "$wid" 2>/dev/null || true
          xdotool windowactivate "$wid" 2>/dev/null || true
          ;;
      esac
      if [ "$geo_changed" = "1" ] || [ "$wid" != "$done_wid" ]; then
        wmctrl -i -r "$wid" -b add,maximized_vert,maximized_horz 2>/dev/null || true
        done_wid="$wid"
      fi
    done
  ) &
  while true; do
    obsidian --no-sandbox --disable-gpu --disable-dev-shm-usage '"$VAULT_DIR"' || true
    echo "[entrypoint] obsidian exited; restarting in 2s" >&2
    sleep 2
  done
'
