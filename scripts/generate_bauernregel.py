#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import socket
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()

DATA_FILE = BASE_DIR / "data" / "bauernregeln.json"
TEMPLATE_DIR = BASE_DIR / "templates" / "display_pages"
TEMPLATE_NAME = "bauernregel.html"
OUTPUT_FILE = BASE_DIR / "pages" / "bauernregel" / "anzeige.html"

MONTHS = {
    1: "Januar",
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


DISPLAY_MONTHS = {
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


def load_rules() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Bauernregel-Datei fehlt: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def pick_rule(rules_for_day: list[str], date_key: str) -> str:
    if not rules_for_day:
        raise ValueError("Leere Bauernregel-Liste erhalten.")

    # Stabil pro Datum: Am selben Tag wird immer dieselbe Regel gewählt.
    digest = hashlib.sha256(date_key.encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(rules_for_day)

    return rules_for_day[index]


def get_rule_for_date(rules: dict, now: datetime) -> tuple[str, str]:
    month_name = MONTHS[now.month]
    day_key = str(now.day)

    month_data = rules.get(month_name)

    if not month_data:
        raise ValueError(f"Kein Monatsblock gefunden: {month_name}")

    rules_for_day = month_data.get(day_key)

    source_label = f"{now.day}. {DISPLAY_MONTHS[now.month]}"

    if not rules_for_day:
        rules_for_day = month_data.get("default")
        source_label = f"{DISPLAY_MONTHS[now.month]} allgemein"

    if not rules_for_day:
        raise ValueError(f"Keine Bauernregel für {month_name} {day_key} und kein default vorhanden.")

    rule = pick_rule(rules_for_day, now.strftime("%Y-%m-%d-%H"))

    return rule, source_label


def render_page() -> str:
    now = datetime.now()

    rules = load_rules()
    rule, source_label = get_rule_for_date(rules, now)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template(TEMPLATE_NAME)

    return template.render(
        headline="Bauernregel",
        date_text=f"{now.day}. {DISPLAY_MONTHS[now.month]} {now.year}",
        updated_text=now.strftime("%d.%m.%Y %H:%M"),
        hostname=socket.gethostname(),
        regel=rule,
        zusatz=f"Quelle: {source_label}",
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
