#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import json
import os
import socket
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()

DATA_FILE = BASE_DIR / "data" / "namenstage.json"
TEMPLATE_DIR = BASE_DIR / "templates" / "display_pages"
TEMPLATE_NAME = "namenstag.html"
OUTPUT_FILE = BASE_DIR / "pages" / "namenstag" / "anzeige.html"

MONTHS = {
    1: "Jänner",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember",
}


def load_names() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Namenstag-Datei fehlt: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def render_page() -> str:
    now = datetime.now()
    key = now.strftime("%m-%d")

    names_data = load_names()
    names = names_data.get(key, [])

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template(TEMPLATE_NAME)

    return template.render(
        date_text=f"{now.day}. {MONTHS[now.month]} {now.year}",
        updated_text=now.strftime("%d.%m.%Y %H:%M"),
        hostname=socket.gethostname(),
        subtitle="Heute feiern Namenstag:" if names else "Keine Einträge gefunden",
        names=names,
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
