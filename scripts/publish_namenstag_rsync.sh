#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/pi/auszeit_display"
EXPORT_DIR="$BASE_DIR/public_export"

REMOTE_USER="DEIN_BENUTZER"
REMOTE_HOST="DEINE_DOMAIN_ODER_SERVER"
REMOTE_PATH="/PFAD/ZUM/WEBROOT"

echo "===== Lokalen Export erstellen ====="
"$BASE_DIR/scripts/export_namenstag_public.sh"

echo "===== Upload per rsync ====="
rsync -avz --delete \
  "$EXPORT_DIR/" \
  "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"

echo "===== Veröffentlichung fertig ====="