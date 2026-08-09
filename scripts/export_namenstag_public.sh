#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR_INPUT="${AUSZEIT_DISPLAY_BASE_DIR:-$SCRIPT_DIR/..}"
BASE_DIR="$(cd -- "$BASE_DIR_INPUT" && pwd)"
EXPORT_DIR="$BASE_DIR/public_export"
PYTHON_BIN="${AUSZEIT_DISPLAY_PYTHON:-$BASE_DIR/venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "FEHLER: Python-Interpreter nicht ausführbar: $PYTHON_BIN" >&2
  exit 1
fi

if [ "$EXPORT_DIR" != "$BASE_DIR/public_export" ] || [ "$EXPORT_DIR" = "/public_export" ]; then
  echo "FEHLER: Unsicherer Exportpfad: $EXPORT_DIR" >&2
  exit 1
fi

echo "===== Namenstag-Seite generieren ====="
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_namenstag.py"

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
