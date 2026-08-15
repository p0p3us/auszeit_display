#!/usr/bin/env python3
from datetime import date, datetime
from pathlib import Path
import json
import os
import socket
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()

DATA_FILE = BASE_DIR / "data" / "weisheiten.json"
TEMPLATE_DIR = BASE_DIR / "templates" / "display_pages"
TEMPLATE_NAME = "weisheit.html"
OUTPUT_FILE = BASE_DIR / "pages" / "weisheit" / "anzeige.html"


def load_weisheiten() -> list[str]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Weisheiten-Datei fehlt: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    weisheiten = data.get("weisheiten")
    if not isinstance(weisheiten, list) or not weisheiten:
        raise ValueError("'weisheiten' muss eine nicht leere Liste sein.")

    if not all(isinstance(text, str) and text.strip() for text in weisheiten):
        raise ValueError("Jede Weisheit muss ein nicht leerer Text sein.")

    return weisheiten


def pick_weisheit(weisheiten: list[str], day: date) -> str:
    """Wählt täglich den nächsten Text und bleibt innerhalb des Tages stabil."""
    index = day.toordinal() % len(weisheiten)
    return weisheiten[index]


def render_page(now: datetime | None = None) -> str:
    now = now or datetime.now()
    weisheit = pick_weisheit(load_weisheiten(), now.date())

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(TEMPLATE_NAME)

    return template.render(
        updated_text=now.strftime("%d.%m.%Y %H:%M"),
        hostname=socket.gethostname(),
        weisheit=weisheit,
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
