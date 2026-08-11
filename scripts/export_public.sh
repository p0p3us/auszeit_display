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

echo "===== Öffentliche Folien generieren ====="
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_namenstag.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_bauernregel.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/fetch_news.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_news.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/fetch_weather.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_weather.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/fetch_menue.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/export_menue.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/fetch_termine.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_termine.py"

echo "===== Export-Ordner vorbereiten ====="
rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR/namenstag"
mkdir -p "$EXPORT_DIR/bauernregel"
mkdir -p "$EXPORT_DIR/static/css/display_pages"
mkdir -p "$EXPORT_DIR/resources/images"
mkdir -p "$EXPORT_DIR/news"
mkdir -p "$EXPORT_DIR/resources/news"
mkdir -p "$EXPORT_DIR/weather"
mkdir -p "$EXPORT_DIR/resources/weather/icons"
mkdir -p "$EXPORT_DIR/menue"
mkdir -p "$EXPORT_DIR/resources/menue"
mkdir -p "$EXPORT_DIR/termine"
mkdir -p "$EXPORT_DIR/resources/termine"

echo "===== HTML exportieren ====="
cp "$BASE_DIR/pages/namenstag/anzeige.html" "$EXPORT_DIR/namenstag/index.html"
cp "$BASE_DIR/pages/bauernregel/anzeige.html" "$EXPORT_DIR/bauernregel/index.html"
cp "$BASE_DIR/pages/news/"*.html "$EXPORT_DIR/news/"
cp "$BASE_DIR/pages/weather/"*.html "$EXPORT_DIR/weather/"
cp "$BASE_DIR/pages/menue/"*.html "$EXPORT_DIR/menue/"
cp "$BASE_DIR/pages/termine/"*.html "$EXPORT_DIR/termine/" 2>/dev/null || true

echo "===== CSS exportieren ====="
cp "$BASE_DIR/static/css/display_pages/base_display.css" "$EXPORT_DIR/static/css/display_pages/base_display.css"
cp "$BASE_DIR/static/css/display_pages/namenstag.css" "$EXPORT_DIR/static/css/display_pages/namenstag.css"
cp "$BASE_DIR/static/css/display_pages/bauernregel.css" "$EXPORT_DIR/static/css/display_pages/bauernregel.css"
cp "$BASE_DIR/static/css/display_pages/news.css" "$EXPORT_DIR/static/css/display_pages/news.css"
cp "$BASE_DIR/static/css/display_pages/weather.css" "$EXPORT_DIR/static/css/display_pages/weather.css"
cp "$BASE_DIR/static/css/display_pages/menue.css" "$EXPORT_DIR/static/css/display_pages/menue.css"
cp "$BASE_DIR/static/css/display_pages/termine.css" "$EXPORT_DIR/static/css/display_pages/termine.css"

echo "===== Bilder exportieren ====="
cp "$BASE_DIR/resources/images/hintergrund.png" "$EXPORT_DIR/resources/images/hintergrund.png"
cp "$BASE_DIR/resources/images/logo.png" "$EXPORT_DIR/resources/images/logo.png"
cp "$BASE_DIR/resources/images/namenstag.png" "$EXPORT_DIR/resources/images/namenstag.png"
cp "$BASE_DIR/resources/images/bauernregel.png" "$EXPORT_DIR/resources/images/bauernregel.png"
cp "$BASE_DIR/resources/images/news.png" "$EXPORT_DIR/resources/images/news.png"

if [ -d "$BASE_DIR/resources/news" ]; then
  cp "$BASE_DIR/resources/news/"* "$EXPORT_DIR/resources/news/" 2>/dev/null || true
fi

if [ -d "$BASE_DIR/resources/weather/icons" ]; then
  cp "$BASE_DIR/resources/weather/icons/"* "$EXPORT_DIR/resources/weather/icons/" 2>/dev/null || true
fi

if [ -d "$BASE_DIR/resources/menue" ]; then
  cp "$BASE_DIR/resources/menue/"* "$EXPORT_DIR/resources/menue/" 2>/dev/null || true
fi

if [ -d "$BASE_DIR/resources/termine" ]; then
  cp "$BASE_DIR/resources/termine/"* "$EXPORT_DIR/resources/termine/" 2>/dev/null || true
fi

for image in \
  menue_tag.png \
  menue_samstag.png \
  menue_fallback.png
do
  if [ -f "$BASE_DIR/resources/images/$image" ]; then
    cp "$BASE_DIR/resources/images/$image" "$EXPORT_DIR/resources/images/$image"
  fi
done

echo "===== Export fertig ====="
find "$EXPORT_DIR" -type f | sort
