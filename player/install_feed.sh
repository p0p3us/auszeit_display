#!/usr/bin/env bash
set -euo pipefail
[ "$(hostname)" = auszeit ] || { echo 'Nur auf Inhaltsserver auszeit ausfuehren.' >&2; exit 1; }
BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[ "$BASE" = /home/pi/auszeit_display ] || { echo 'Unerwarteter Repositorypfad.' >&2; exit 1; }
test -x "$BASE/venv/bin/python"
test -f "$BASE/config/publish.env"
sudo tee /etc/systemd/system/auszeit-player-feed.service >/dev/null <<'EOF'
[Unit]
Description=Auszeit separate player content feed
After=network-online.target auszeit-publish-public.service
Wants=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/auszeit_display
ExecStart=/bin/bash /home/pi/auszeit_display/player/publish_feed.sh
TimeoutStartSec=10min
UMask=0077
NoNewPrivileges=true
EOF
sudo tee /etc/systemd/system/auszeit-player-feed.timer >/dev/null <<'EOF'
[Unit]
Description=Auszeit hourly player feed publication

[Timer]
OnBootSec=3min
OnCalendar=*-*-* *:06:00
Persistent=true
AccuracySec=1s
Unit=auszeit-player-feed.service

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now auszeit-player-feed.timer
sudo systemctl start auszeit-player-feed.service
echo 'Player-Feed-Timer installiert und erster Lauf abgeschlossen.'
