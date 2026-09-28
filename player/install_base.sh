#!/usr/bin/env bash
# Fresh reference device only. Never run on the working player or content server.
set -euo pipefail
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[ "$(hostname)" = auszeit-player-01 ] || { echo 'Falscher Hostname.' >&2; exit 1; }
[ "$(uname -m)" = aarch64 ] || { echo '64-Bit-System erforderlich.' >&2; exit 1; }
grep -q 'Raspberry Pi 4' /proc/device-tree/model || { echo 'Pi 4 erforderlich.' >&2; exit 1; }
. /etc/os-release
[ "$VERSION_ID" = 13 ] || { echo 'Trixie erforderlich.' >&2; exit 1; }
id auszeit >/dev/null
if id player >/dev/null 2>&1 || sudo test -e /etc/auszeit-player || sudo test -e /opt/auszeit-player-package-test; then
  echo 'Abbruch: Player bereits eingerichtet. Dieser Installer ist nur fuer ein frisches System.' >&2
  exit 1
fi
sudo apt-get update
sudo apt-get install -y --no-install-recommends labwc chromium chromium-sandbox dbus-user-session \
  wlr-randr fonts-dejavu-core fonts-liberation rpi-connect-lite iw
sudo timedatectl set-timezone Europe/Vienna
sudo timedatectl set-ntp true
sudo useradd --create-home --user-group --shell /bin/bash player
sudo passwd --lock player
sudo install -d -o player -g player -m 0700 /home/player/.config
sudo install -d -o player -g player -m 0755 /home/player/.config/labwc /home/player/.config/systemd /home/player/.config/systemd/user
sudo install -d -o player -g player -m 0700 /home/player/.config/chromium
sudo tee /home/player/.bash_profile >/dev/null <<'EOF'
if [ "$(tty)" = "/dev/tty1" ]; then
    export XDG_SESSION_TYPE=wayland
    exec dbus-run-session -- labwc >"$HOME/display.log" 2>&1
fi
EOF
sudo tee /home/player/.config/labwc/autostart >/dev/null <<'EOF'
#!/bin/sh
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
systemctl --user import-environment WAYLAND_DISPLAY XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS
systemctl --user daemon-reload
systemctl --user restart auszeit-browser.service &
EOF
sudo tee /home/player/.config/systemd/user/auszeit-browser.service >/dev/null <<'EOF'
[Unit]
Description=Auszeit kiosk browser
StartLimitIntervalSec=0
[Service]
Type=exec
ExecStart=/usr/bin/chromium --ozone-platform=wayland --kiosk --no-first-run --noerrdialogs --user-data-dir=/home/player/.config/chromium http://127.0.0.1:8081/
Restart=always
RestartSec=5
TimeoutStopSec=10
KillMode=control-group
EOF
sudo chown player:player /home/player/.bash_profile /home/player/.config/labwc/autostart /home/player/.config/systemd/user/auszeit-browser.service
sudo chmod 0755 /home/player/.config/labwc/autostart
sudo install -d -m 0755 /etc/chromium/policies/managed /etc/NetworkManager/conf.d /etc/systemd/system/getty@tty1.service.d
sudo tee /etc/chromium/policies/managed/auszeit-player.json >/dev/null <<'EOF'
{"TranslateEnabled": false}
EOF
sudo tee /etc/NetworkManager/conf.d/90-auszeit-wifi.conf >/dev/null <<'EOF'
[connection]
wifi.powersave=2
EOF
sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf >/dev/null <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin player --noclear %I $TERM
EOF
sudo loginctl enable-linger auszeit
bash "$SOURCE/operations/install.sh"
echo 'Basis installiert. Nach Neustart Netzwerk/Anzeige pruefen, Connect und Geraetetoken separat einrichten.'
