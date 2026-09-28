#!/usr/bin/env bash
set -euo pipefail
if [ "$(hostname)" != "auszeit-player-01" ]; then
  echo "Nur auf dem Anzeige-Pi auszeit-player-01 ausfuehren." >&2
  exit 1
fi
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# Update playback/heartbeat first, retaining the existing verified content.
bash "$SOURCE/package_test/install.sh"
DEST=/opt/auszeit-player-package-test
sudo install -d -m 0755 "$DEST/player/operations"
sudo install -m 0644 "$SOURCE/operations/run.py" "$DEST/player/operations/run.py"
sudo install -d -o root -g player -m 0750 /etc/auszeit-player
sudo install -d -o player -g player -m 0750 /var/lib/auszeit-player-operations
if ! sudo test -e /etc/auszeit-player/config.json; then
  sudo /usr/bin/python3 - <<'PY'
import json, os, socket, uuid
from pathlib import Path
path = Path('/etc/auszeit-player/config.json')
with path.open('x') as output:
    json.dump({'device_id': socket.gethostname() + '-' + uuid.uuid4().hex[:12],
               'feed_url': None, 'status_url': None,
               'token_file': '/etc/auszeit-player/status.token'}, output, indent=2)
os.chmod(path, 0o640)
PY
  sudo chown root:player /etc/auszeit-player/config.json
fi
sudo tee /etc/systemd/system/auszeit-player-sync.service >/dev/null <<'EOF'
[Unit]
Description=Auszeit verified content update and status
After=network.target auszeit-player-packages.service

[Service]
Type=oneshot
User=player
Group=player
WorkingDirectory=/opt/auszeit-player-package-test
ExecStart=/usr/bin/python3 -m player.operations.run
TimeoutStartSec=240
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/auszeit-player-package-test /var/lib/auszeit-player-operations
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
EOF
sudo tee /etc/systemd/system/auszeit-player-sync.timer >/dev/null <<'EOF'
[Unit]
Description=Auszeit content/status interval

[Timer]
OnBootSec=60
OnUnitInactiveSec=5min
RandomizedDelaySec=45
AccuracySec=1s
Unit=auszeit-player-sync.service

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now auszeit-player-sync.timer
sudo systemctl start auszeit-player-sync.service
echo "Automatik installiert. Ohne konfigurierte URLs wird nur der lokale Status geschrieben."
