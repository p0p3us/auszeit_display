#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

PROJECT_DIR = Path(os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)).expanduser().resolve()
DATA_FILE = PROJECT_DIR / "data" / "termine.json"
TEMPLATE_DIR = PROJECT_DIR / "templates" / "display_pages"
OUTPUT_DIR = PROJECT_DIR / "pages" / "termine"
WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
MONTHS = ("", "Jänner", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")


def log(message: str) -> None:
    print(f"[generate_termine] {message}", flush=True)


def format_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{WEEKDAYS[parsed.weekday()]}, {parsed.day}. {MONTHS[parsed.month]} {parsed.year}"


def load_events() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return []
    events = payload.get("events", [])
    return events if isinstance(events, list) else []


def main() -> int:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html", "xml"]))
    template = environment.get_template("termin.html")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    expected: set[str] = set()
    for index, event in enumerate(load_events(), start=1):
        filename = f"termin-{index}.html"
        expected.add(filename)
        context = dict(event)
        context["date_text"] = format_date(str(event["date"]))
        output = OUTPUT_DIR / filename
        temporary = output.with_suffix(".html.tmp")
        temporary.write_text(template.render(event=context), encoding="utf-8")
        temporary.replace(output)
        log(f"Erzeugt: {output}")
    for old_file in OUTPUT_DIR.glob("termin-*.html"):
        if old_file.name not in expected:
            old_file.unlink()
            log(f"Veraltete Folie entfernt: {old_file}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        log(f"Generierung fehlgeschlagen: {exc}")
        sys.exit(1)
