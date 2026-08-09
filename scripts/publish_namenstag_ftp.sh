#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR_INPUT="${AUSZEIT_DISPLAY_BASE_DIR:-$SCRIPT_DIR/..}"
BASE_DIR="$(cd -- "$BASE_DIR_INPUT" && pwd)"
EXPORT_DIR="$BASE_DIR/public_export"
CONFIG_FILE="$BASE_DIR/config/publish.env"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "FEHLER: Config-Datei fehlt: $CONFIG_FILE" >&2
  exit 1
fi

source "$CONFIG_FILE"

: "${FTP_HOST:?FEHLER: FTP_HOST fehlt in $CONFIG_FILE}"
: "${FTP_USER:?FEHLER: FTP_USER fehlt in $CONFIG_FILE}"
: "${FTP_PASS:?FEHLER: FTP_PASS fehlt in $CONFIG_FILE}"
: "${FTP_REMOTE_DIR:?FEHLER: FTP_REMOTE_DIR fehlt in $CONFIG_FILE}"

if [ "$FTP_REMOTE_DIR" = "/" ] || [ "$FTP_REMOTE_DIR" = "." ]; then
  echo "FEHLER: Unsicheres FTP-Ziel für --delete: $FTP_REMOTE_DIR" >&2
  exit 1
fi

NAMENSTAG_REMOTE_DIR="${FTP_REMOTE_DIR%/}/namenstag"

echo "===== Lokalen Export erstellen ====="
"$BASE_DIR/scripts/export_namenstag_public.sh"

if [ ! -d "$EXPORT_DIR/namenstag" ] || [ ! -f "$EXPORT_DIR/namenstag/index.html" ]; then
  echo "FEHLER: Export ist unvollständig; Upload abgebrochen: $EXPORT_DIR" >&2
  exit 1
fi

echo "===== FTP Upload starten ====="
lftp -u "$FTP_USER","$FTP_PASS" "ftp://$FTP_HOST" <<EOF
set ftp:ssl-allow no
mkdir -p "$NAMENSTAG_REMOTE_DIR"
mirror -R --delete "$EXPORT_DIR/namenstag" "$NAMENSTAG_REMOTE_DIR"
bye
EOF

echo "===== Veröffentlichung fertig ====="
echo "Online: https://populorum.eu/auszeit-display/namenstag/"
