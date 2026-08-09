#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/pi/auszeit_display"
EXPORT_DIR="$BASE_DIR/public_export"

echo "===== Namenstag-Seite generieren ====="
"$BASE_DIR/venv/bin/python" "$BASE_DIR/scripts/generate_namenstag.py"

echo "===== Export-Ordner vorbereiten ====="
rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR/namenstag"
mkdir -p "$EXPORT_DIR/static/css/display_pages"
mkdir -p "$EXPORT_DIR/resources/images"

echo "===== HTML exportieren ====="
cp "$BASE_DIR/pages/namenstag/anzeige.html" "$EXPORT_DIR/namenstag/index.html"

echo "===== CSS exportieren ====="
cp "$BASE_DIR/static/css/display_pages/base_display.css" "$EXPORT_DIR/static/css/display_pages/base_display.css"
cp "$BASE_DIR/static/css/display_pages/namenstag.css" "$EXPORT_DIR/static/css/display_pages/namenstag.css"

echo "===== Bilder exportieren ====="
cp "$BASE_DIR/resources/images/hintergrund.png" "$EXPORT_DIR/resources/images/hintergrund.png"
cp "$BASE_DIR/resources/images/logo.png" "$EXPORT_DIR/resources/images/logo.png"
cp "$BASE_DIR/resources/images/namenstag.png" "$EXPORT_DIR/resources/images/namenstag.png"

echo "===== Export fertig ====="
find "$EXPORT_DIR" -type f | sort