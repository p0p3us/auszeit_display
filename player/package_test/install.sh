#!/usr/bin/env bash
set -euo pipefail
if [ "$(hostname)" != "auszeit-player-01" ]; then
  echo "Abbruch: Nur auf dem Anzeige-Pi auszeit-player-01 installieren." >&2
  exit 1
fi
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
for file in local_test/server.py local_test/web/index.html local_test/web/app.js local_test/web/style.css update_test/updater.py update_test/exercise.py package_test/server.py package_test/publish.py; do
  test -f "$SOURCE/$file" || { echo "Datei fehlt: $file" >&2; exit 1; }
done
sudo -v
sudo test -f /home/player/.config/systemd/user/auszeit-browser.service || { echo "Browserdienst fehlt." >&2; exit 1; }
DEST=/opt/auszeit-player-package-test
for folder in local_test local_test/web update_test package_test; do
  sudo install -d -m 0755 "$DEST/player/$folder"
done
for file in local_test/server.py local_test/web/index.html local_test/web/app.js local_test/web/style.css update_test/updater.py update_test/exercise.py package_test/server.py package_test/publish.py; do
  sudo install -m 0644 "$SOURCE/$file" "$DEST/player/$file"
done
sudo install -d -o player -g player -m 0750 /var/lib/auszeit-player-package-test
# Seed through the real downloader, then shut down the temporary loopback feed.
(cd "$DEST" && sudo -u player /usr/bin/python3 -m player.package_test.publish init)
sudo tee /etc/systemd/system/auszeit-player-packages.service >/dev/null <<'EOF'
[Unit]
Description=Auszeit verified synthetic package playback
After=local-fs.target

[Service]
User=player
Group=player
WorkingDirectory=/opt/auszeit-player-package-test
ExecStart=/usr/bin/python3 -m player.package_test.server
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
RestrictAddressFamilies=AF_INET AF_UNIX

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable auszeit-player-packages.service
sudo systemctl restart auszeit-player-packages.service
for attempt in 1 2 3 4 5; do
  if /usr/bin/python3 -c 'import json, urllib.request; s=json.load(urllib.request.urlopen("http://127.0.0.1:8081/api/state",timeout=2)); assert s["slide"] and not s["last_error"]' 2>/dev/null; then
    break
  fi
  if [ "$attempt" = 5 ]; then
    echo "Paketdienst nicht bereit; Browser bleibt unveraendert." >&2
    exit 1
  fi
  sleep 1
done
sudo install -d -o player -g player /home/player/.config/systemd/user/auszeit-browser.service.d
sudo tee /home/player/.config/systemd/user/auszeit-browser.service.d/packages-test.conf >/dev/null <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/chromium --ozone-platform=wayland --kiosk --no-first-run --noerrdialogs --user-data-dir=/home/player/.config/chromium http://127.0.0.1:8081/
EOF
sudo chown player:player /home/player/.config/systemd/user/auszeit-browser.service.d/packages-test.conf
sudo systemctl restart getty@tty1.service
echo "Paketwiedergabe eingerichtet: Folien A/B/C aus gespeichertem Inhaltsstand."
