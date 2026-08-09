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

: "${RSYNC_REMOTE_USER:?FEHLER: RSYNC_REMOTE_USER fehlt in $CONFIG_FILE}"
: "${RSYNC_REMOTE_HOST:?FEHLER: RSYNC_REMOTE_HOST fehlt in $CONFIG_FILE}"
: "${RSYNC_REMOTE_PATH:?FEHLER: RSYNC_REMOTE_PATH fehlt in $CONFIG_FILE}"

if [ "$RSYNC_REMOTE_PATH" = "/" ] || [ "$RSYNC_REMOTE_PATH" = "." ]; then
  echo "FEHLER: Unsicheres rsync-Ziel für --delete: $RSYNC_REMOTE_PATH" >&2
  exit 1
fi

NAMENSTAG_REMOTE_PATH="${RSYNC_REMOTE_PATH%/}/namenstag"

echo "===== Lokalen Export erstellen ====="
"$BASE_DIR/scripts/export_namenstag_public.sh"

if [ ! -d "$EXPORT_DIR/namenstag" ] || [ ! -f "$EXPORT_DIR/namenstag/index.html" ]; then
  echo "FEHLER: Export ist unvollständig; Upload abgebrochen: $EXPORT_DIR" >&2
  exit 1
fi

echo "===== Upload per rsync ====="
rsync -avz --delete \
  "$EXPORT_DIR/namenstag/" \
  "$RSYNC_REMOTE_USER@$RSYNC_REMOTE_HOST:$NAMENSTAG_REMOTE_PATH/"

echo "===== Veröffentlichung fertig ====="
