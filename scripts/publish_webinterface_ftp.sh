#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR_INPUT="${AUSZEIT_DISPLAY_BASE_DIR:-$SCRIPT_DIR/..}"
BASE_DIR="$(cd -- "$BASE_DIR_INPUT" && pwd)"
WEB_DIR="$BASE_DIR/webinterface"
CONFIG_FILE="$BASE_DIR/config/publish.env"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "FEHLER: Config-Datei fehlt: $CONFIG_FILE" >&2
  exit 1
fi

source "$CONFIG_FILE"

: "${FTP_HOST:?FEHLER: FTP_HOST fehlt in $CONFIG_FILE}"
: "${FTP_USER:?FEHLER: FTP_USER fehlt in $CONFIG_FILE}"
: "${FTP_PASS:?FEHLER: FTP_PASS fehlt in $CONFIG_FILE}"
: "${WEBINTERFACE_REMOTE_DIR:?FEHLER: WEBINTERFACE_REMOTE_DIR fehlt in $CONFIG_FILE}"

case "$WEBINTERFACE_REMOTE_DIR" in
  /menu_admin|/menu_admin/) ;;
  *)
    echo "FEHLER: Unerwartetes Webinterface-Ziel: $WEBINTERFACE_REMOTE_DIR" >&2
    echo "Erlaubt ist ausschließlich /menu_admin." >&2
    exit 1
    ;;
esac

required_files=(
  menu_admin.php
  termine-admin.php
  menu-layout.php
  termine-layout.php
  preview-menu.php
  preview-termine.php
  includes/bootstrap.php
  includes/auth.php
  includes/storage.php
  assets/gold.jpg
  assets/leather.jpg
)

for relative_path in "${required_files[@]}"; do
  if [ ! -f "$WEB_DIR/$relative_path" ]; then
    echo "FEHLER: Webinterface-Datei fehlt: $WEB_DIR/$relative_path" >&2
    exit 1
  fi
done

echo "===== Webinterface-Quellcode hochladen ====="
lftp -u "$FTP_USER","$FTP_PASS" "ftp://$FTP_HOST" <<EOF
set ftp:ssl-allow no
mkdir -p "$WEBINTERFACE_REMOTE_DIR"
mkdir -p "$WEBINTERFACE_REMOTE_DIR/includes"
mkdir -p "$WEBINTERFACE_REMOTE_DIR/assets"
put "$WEB_DIR/menu_admin.php" -o "$WEBINTERFACE_REMOTE_DIR/menu_admin.php"
put "$WEB_DIR/termine-admin.php" -o "$WEBINTERFACE_REMOTE_DIR/termine-admin.php"
put "$WEB_DIR/menu-layout.php" -o "$WEBINTERFACE_REMOTE_DIR/menu-layout.php"
put "$WEB_DIR/termine-layout.php" -o "$WEBINTERFACE_REMOTE_DIR/termine-layout.php"
put "$WEB_DIR/preview-menu.php" -o "$WEBINTERFACE_REMOTE_DIR/preview-menu.php"
put "$WEB_DIR/preview-termine.php" -o "$WEBINTERFACE_REMOTE_DIR/preview-termine.php"
put "$WEB_DIR/includes/bootstrap.php" -o "$WEBINTERFACE_REMOTE_DIR/includes/bootstrap.php"
put "$WEB_DIR/includes/auth.php" -o "$WEBINTERFACE_REMOTE_DIR/includes/auth.php"
put "$WEB_DIR/includes/storage.php" -o "$WEBINTERFACE_REMOTE_DIR/includes/storage.php"
put "$WEB_DIR/assets/gold.jpg" -o "$WEBINTERFACE_REMOTE_DIR/assets/gold.jpg"
put "$WEB_DIR/assets/leather.jpg" -o "$WEBINTERFACE_REMOTE_DIR/assets/leather.jpg"
bye
EOF

echo "===== Webinterface-Upload fertig ====="
echo "Laufzeitdaten und config/local.php wurden nicht angefasst."
