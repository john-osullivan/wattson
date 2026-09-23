# WATTSON Phase-0 spike: full Obsidian desktop in a container under Xvfb.
# Iteration speed over minimalism; not a production image.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget \
        xvfb x11vnc novnc nox nginx \
        libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 \
        libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
        libxrandr2 libgbm1 libasound2t64 libpango-1.0-0 libcairo2 \
        libgtk-3-0t64 libxss1 libsecret-1-0 \
        dbus-x11 fontconfig fonts-liberation \
        xdotool scrot tesseract-ocr python3-pil \
    && rm -rf /var/lib/apt/lists/*

# Desktop app with the `obsidian` CLI. v1.13.7 = newest release shipping an amd64 .deb.
ARG OBSIDIAN_VERSION=1.13.7
RUN wget -q "https://github.com/obsidianmd/obsidian-releases/releases/download/v${OBSIDIAN_VERSION}/obsidian_${OBSIDIAN_VERSION}_amd64.deb" -O /tmp/obsidian.deb \
    && apt-get update \
    && apt-get install -y /tmp/obsidian.deb \
    && rm -f /tmp/obsidian.deb \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# 5900 = VNC (x11vnc), 6080 = noVNC web client
EXPOSE 5900 6080

VOLUME ["/data/vault", "/data/state", "/root/.config/obsidian"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
