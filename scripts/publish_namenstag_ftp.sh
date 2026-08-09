#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/pi/auszeit_display"
EXPORT_DIR="$BASE_DIR/public_export"
CONFIG_FILE="$BASE_DIR/config/publish.env"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "FEHLER: Config-Datei fehlt: $CONFIG_FILE" >&2
  exit 1
fi

source "$CONFIG_FILE"

echo "===== Lokalen Export erstellen ====="
"$BASE_DIR/scripts/export_namenstag_public.sh"

echo "===== FTP Upload starten ====="
lftp -u "$FTP_USER","$FTP_PASS" "ftp://$FTP_HOST" <<EOF
set ftp:ssl-allow no
mkdir -p "$FTP_REMOTE_DIR"
mirror -R --delete "$EXPORT_DIR" "$FTP_REMOTE_DIR"
bye
EOF

echo "===== Veröffentlichung fertig ====="
echo "Online: https://populorum.eu/auszeit-display/namenstag/"