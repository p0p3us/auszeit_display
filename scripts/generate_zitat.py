#!/usr/bin/env python3
from datetime import date, datetime
from pathlib import Path
import json
import os
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()

DATA_FILE = BASE_DIR / "data" / "zitate.json"
TEMPLATE_DIR = BASE_DIR / "templates" / "display_pages"
TEMPLATE_NAME = "zitat.html"
OUTPUT_FILE = BASE_DIR / "pages" / "zitat" / "anzeige.html"


def load_zitate() -> list[dict]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Zitate-Datei fehlt: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    zitate = data.get("zitate")
    if not isinstance(zitate, list) or not zitate:
        raise ValueError("'zitate' muss eine nicht leere Liste sein.")

    required = {"text", "autor", "beschreibung", "bild"}
    for number, entry in enumerate(zitate, start=1):
        if not isinstance(entry, dict) or not required.issubset(entry):
            raise ValueError(f"Zitat {number} ist unvollständig.")
        if not all(isinstance(entry[key], str) for key in required):
            raise ValueError(f"Zitat {number} enthält ungültige Pflichtfelder.")
        if not all(entry[key].strip() for key in {"text", "autor", "bild"}):
            raise ValueError(f"Zitat {number} enthält leere Pflichtfelder.")
        image = BASE_DIR / "resources" / "zitate" / entry["bild"]
        if not image.is_file():
            raise FileNotFoundError(f"Kopfbild fehlt: {image}")

    return zitate


def pick_zitat(zitate: list[dict], day: date) -> dict:
    """Wählt täglich den nächsten Eintrag und bleibt innerhalb des Tages stabil."""
    return zitate[day.toordinal() % len(zitate)]


def lebensdaten(entry: dict) -> str:
    born = entry.get("geburtsjahr")
    died = entry.get("sterbejahr")
    if born and died:
        return f"{born}–{died}"
    if born:
        return f"geb. {born}"
    return ""


def render_page(now: datetime | None = None) -> str:
    now = now or datetime.now()
    zitat = pick_zitat(load_zitate(), now.date())

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(TEMPLATE_NAME)

    return template.render(
        zitat=zitat,
        lebensdaten=lebensdaten(zitat),
    )


def main() -> int:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(render_page(), encoding="utf-8")
    print(f"OK: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        raise SystemExit(1)
