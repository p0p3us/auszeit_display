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

if ! command -v rsync >/dev/null 2>&1; then
  echo "FEHLER: rsync ist nicht installiert." >&2
  exit 1
fi

STAGING_DIR="$(mktemp -d "$BASE_DIR/.public_export.XXXXXX")"

cleanup() {
  case "$STAGING_DIR" in
    "$BASE_DIR"/.public_export.*)
      rm -rf -- "$STAGING_DIR"
      ;;
  esac
}

trap cleanup EXIT

echo "===== Öffentliche Folien generieren ====="
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_namenstag.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_bauernregel.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_weisheit.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/fetch_news.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_news.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/fetch_weather.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_weather.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/fetch_menue.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/export_menue.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/fetch_termine.py"
"$PYTHON_BIN" "$BASE_DIR/scripts/generate_termine.py"

echo "===== Export-Ordner vorbereiten ====="
mkdir -p "$STAGING_DIR/namenstag"
mkdir -p "$STAGING_DIR/bauernregel"
mkdir -p "$STAGING_DIR/weisheit"
mkdir -p "$STAGING_DIR/static/css/display_pages"
mkdir -p "$STAGING_DIR/resources/images"
mkdir -p "$STAGING_DIR/news"
mkdir -p "$STAGING_DIR/resources/news"
mkdir -p "$STAGING_DIR/weather"
mkdir -p "$STAGING_DIR/resources/weather/icons"
mkdir -p "$STAGING_DIR/menue"
mkdir -p "$STAGING_DIR/resources/menue"
mkdir -p "$STAGING_DIR/termine"
mkdir -p "$STAGING_DIR/resources/termine"

echo "===== HTML exportieren ====="
cp "$BASE_DIR/pages/namenstag/anzeige.html" "$STAGING_DIR/namenstag/index.html"
cp "$BASE_DIR/pages/bauernregel/anzeige.html" "$STAGING_DIR/bauernregel/index.html"
cp "$BASE_DIR/pages/weisheit/anzeige.html" "$STAGING_DIR/weisheit/index.html"
cp "$BASE_DIR/pages/news/"*.html "$STAGING_DIR/news/"
cp "$BASE_DIR/pages/weather/"*.html "$STAGING_DIR/weather/"
cp "$BASE_DIR/pages/menue/"*.html "$STAGING_DIR/menue/"
cp "$BASE_DIR/pages/termine/"*.html "$STAGING_DIR/termine/" 2>/dev/null || true

echo "===== CSS exportieren ====="
cp "$BASE_DIR/static/css/display_pages/base_display.css" "$STAGING_DIR/static/css/display_pages/base_display.css"
cp "$BASE_DIR/static/css/display_pages/namenstag.css" "$STAGING_DIR/static/css/display_pages/namenstag.css"
cp "$BASE_DIR/static/css/display_pages/bauernregel.css" "$STAGING_DIR/static/css/display_pages/bauernregel.css"
cp "$BASE_DIR/static/css/display_pages/weisheit.css" "$STAGING_DIR/static/css/display_pages/weisheit.css"
cp "$BASE_DIR/static/css/display_pages/news.css" "$STAGING_DIR/static/css/display_pages/news.css"
cp "$BASE_DIR/static/css/display_pages/weather.css" "$STAGING_DIR/static/css/display_pages/weather.css"
cp "$BASE_DIR/static/css/display_pages/menue.css" "$STAGING_DIR/static/css/display_pages/menue.css"
cp "$BASE_DIR/static/css/display_pages/termine.css" "$STAGING_DIR/static/css/display_pages/termine.css"

echo "===== Bilder exportieren ====="
cp "$BASE_DIR/resources/images/hintergrund.png" "$STAGING_DIR/resources/images/hintergrund.png"
cp "$BASE_DIR/resources/images/logo.png" "$STAGING_DIR/resources/images/logo.png"
cp "$BASE_DIR/resources/images/namenstag.png" "$STAGING_DIR/resources/images/namenstag.png"
cp "$BASE_DIR/resources/images/bauernregel.png" "$STAGING_DIR/resources/images/bauernregel.png"
cp "$BASE_DIR/resources/images/weisheit.png" "$STAGING_DIR/resources/images/weisheit.png"
cp "$BASE_DIR/resources/images/news.png" "$STAGING_DIR/resources/images/news.png"

if [ -d "$BASE_DIR/resources/news" ]; then
  cp "$BASE_DIR/resources/news/"* "$STAGING_DIR/resources/news/" 2>/dev/null || true
fi

if [ -d "$BASE_DIR/resources/weather/icons" ]; then
  cp "$BASE_DIR/resources/weather/icons/"* "$STAGING_DIR/resources/weather/icons/" 2>/dev/null || true
fi

if [ -d "$BASE_DIR/resources/menue" ]; then
  cp "$BASE_DIR/resources/menue/"* "$STAGING_DIR/resources/menue/" 2>/dev/null || true
fi

if [ -d "$BASE_DIR/resources/termine" ]; then
  cp "$BASE_DIR/resources/termine/"* "$STAGING_DIR/resources/termine/" 2>/dev/null || true
fi

for image in \
  menue_tag.png \
  menue_samstag.png \
  menue_fallback.png
do
  if [ -f "$BASE_DIR/resources/images/$image" ]; then
    cp "$BASE_DIR/resources/images/$image" "$STAGING_DIR/resources/images/$image"
  fi
done

echo "===== Änderungen mit Public-Export abgleichen ====="
mkdir -p "$EXPORT_DIR"
rsync -r --delete --checksum --itemize-changes "$STAGING_DIR/" "$EXPORT_DIR/"

echo "===== Export fertig ====="
find "$EXPORT_DIR" -type f | sort
