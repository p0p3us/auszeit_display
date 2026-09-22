#!/usr/bin/env bash
# Local prototype only. Run on the separately provisioned display Pi.
set -euo pipefail
if [ "$(hostname)" != "auszeit-player-01" ]; then
  echo "Abbruch: Installation nur auf auszeit-player-01, niemals auf dem Inhaltsserver."
  exit 1
fi
id player >/dev/null
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for file in server.py web/index.html web/slide.html web/style.css web/app.js; do
  test -f "$SOURCE/$file"
done
test -x /usr/bin/python3
test -f /home/player/.config/systemd/user/auszeit-browser.service
sudo install -d -m 0755 /opt/auszeit-player-test /opt/auszeit-player-test/web
sudo install -m 0644 "$SOURCE/server.py" /opt/auszeit-player-test/server.py
for file in index.html slide.html style.css app.js; do
  sudo install -m 0644 "$SOURCE/web/$file" "/opt/auszeit-player-test/web/$file"
done
sudo tee /etc/systemd/system/auszeit-player-test.service >/dev/null <<'EOF'
[Unit]
Description=Auszeit local slideshow test (no production feed)
After=local-fs.target

[Service]
User=player
Group=player
Environment=AUSZEIT_TEST_SCENARIO=expiry
EnvironmentFile=-/etc/default/auszeit-player-test
ExecStart=/usr/bin/python3 /opt/auszeit-player-test/server.py --scenario ${AUSZEIT_TEST_SCENARIO}
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
sudo systemctl enable auszeit-player-test.service
sudo systemctl restart auszeit-player-test.service
# Health check does not start the timed demo.
for attempt in 1 2 3 4 5; do
  if /usr/bin/python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8080/healthz", timeout=2).read()' 2>/dev/null; then
    break
  fi
  if [ "$attempt" = 5 ]; then
    echo "Lokaler Dienst nicht erreichbar; Browser bleibt unverändert."
    exit 1
  fi
  sleep 1
done
sudo install -d -o player -g player /home/player/.config/systemd/user/auszeit-browser.service.d
sudo tee /home/player/.config/systemd/user/auszeit-browser.service.d/local-test.conf >/dev/null <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/chromium --ozone-platform=wayland --kiosk --no-first-run --noerrdialogs --user-data-dir=/home/player/.config/chromium http://127.0.0.1:8080/
EOF
sudo chown player:player /home/player/.config/systemd/user/auszeit-browser.service.d/local-test.conf
sudo systemctl restart getty@tty1.service
echo "Wechseltest installiert: A, B, C, kurz A; nach 65 Sekunden Ersatzseite."
