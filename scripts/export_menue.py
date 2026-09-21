#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


PROJECT_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()

DATA_FILE = PROJECT_DIR / "data" / "menue.json"
STATUS_FILE = PROJECT_DIR / "data" / "menue_status.json"

TEMPLATE_DIR = PROJECT_DIR / "templates" / "display_pages"
OUTPUT_DIR = PROJECT_DIR / "pages" / "menue"

OVERVIEW_TEMPLATE = "menue_uebersicht.html"
DAY_TEMPLATE = "menue_tag.html"
WEEKLY_TEMPLATE = "menue_wochenschmankerl.html"


FALLBACKS = {
    "overview": {
        "headline": "Der Menüplan macht sich noch fein.",
        "text": (
            "Sobald die Küche entschieden hat, womit sie uns diese Woche "
            "verwöhnt, steht es genau hier."
        ),
        "footer": "Bis dahin: Kaffee geht bekanntlich immer.",
    },
    "weekly": {
        "headline": "Das Wochenschmankerl folgt.",
        "text": (
            "Sobald die Küche das besondere Gericht festgelegt hat, steht es hier."
        ),
        "footer": "Die aktuellen Mittagsmenüs sind bereits auf unseren anderen Folien zu sehen.",
    },
    "today": {
        "headline": "Heute kein Mittagsmenü?",
        "text": (
            "Dann ist das vermutlich ein Wink des Schicksals, "
            "länger beim Kaffee zu bleiben."
        ),
        "footer": "Schön, dass Sie da sind.",
    },
    "tomorrow": {
        "headline": "Morgen ist noch nicht angerichtet.",
        "text": (
            "Die Küche tüftelt vermutlich noch an etwas besonders Gutem."
        ),
        "footer": "Vorfreude hat schließlich auch keine Kalorien.",
    },
}


WEEKDAY_NAMES = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag",
}


MONTH_NAMES = {
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


def log(message: str) -> None:
    print(f"[export_menue] {message}", flush=True)


def load_menu_data() -> dict[str, Any] | None:
    if not DATA_FILE.exists():
        log(f"Datendatei fehlt: {DATA_FILE}")
        return None

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        log(f"Menüdaten konnten nicht gelesen werden: {exc}")
        return None

    if data.get("status") != "ok":
        log("Menüdaten besitzen keinen gültigen Status.")
        return None

    return data


def parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def format_date(value: date | None) -> str:
    if value is None:
        return ""

    return (
        f"{WEEKDAY_NAMES[value.weekday()]}, "
        f"{value.day}. {MONTH_NAMES[value.month]} {value.year}"
    )


def format_short_date(value: date | None) -> str:
    if value is None:
        return ""

    return f"{value.day}. {MONTH_NAMES[value.month]}"


def format_period(start_date: date | None, end_date: date | None) -> str:
    if start_date is None or end_date is None:
        return ""

    if start_date.year == end_date.year and start_date.month == end_date.month:
        return (
            f"{start_date.day}. bis {end_date.day}. "
            f"{MONTH_NAMES[end_date.month]} {end_date.year}"
        )

    if start_date.year == end_date.year:
        return (
            f"{start_date.day}. {MONTH_NAMES[start_date.month]} bis "
            f"{end_date.day}. {MONTH_NAMES[end_date.month]} "
            f"{end_date.year}"
        )

    return (
        f"{start_date.day}. {MONTH_NAMES[start_date.month]} "
        f"{start_date.year} bis "
        f"{end_date.day}. {MONTH_NAMES[end_date.month]} "
        f"{end_date.year}"
    )


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def normalize_menu_entry(entry: dict[str, Any]) -> dict[str, Any]:
    menu_date = parse_iso_date(entry.get("date"))

    return {
        "weekday": clean_text(entry.get("weekday")),
        "date": menu_date,
        "date_text": format_short_date(menu_date),
        "full_date_text": format_date(menu_date),
        "soup": clean_text(entry.get("soup")) or "Tagessuppe",
        "title": clean_text(entry.get("title")),
        "description": clean_text(entry.get("description")),
        "price": clean_text(entry.get("price")),
    }


def get_valid_days(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not data:
        return []

    raw_days = data.get("days")

    if not isinstance(raw_days, list):
        return []

    days: list[dict[str, Any]] = []

    for raw_entry in raw_days:
        if not isinstance(raw_entry, dict):
            continue

        entry = normalize_menu_entry(raw_entry)

        if entry["date"] is None:
            continue

        if not entry["title"]:
            continue

        days.append(entry)

    days.sort(key=lambda item: item["date"])

    return days


def find_menu_for_date(
    days: list[dict[str, Any]],
    wanted_date: date,
) -> dict[str, Any] | None:
    for entry in days:
        if entry["date"] == wanted_date:
            return entry

    return None


def get_weekly_special(
    data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not data:
        return None

    if data.get("has_weekly_special") is not True:
        return None

    raw_special = data.get("weekly_special")

    if not isinstance(raw_special, dict):
        return None

    title = clean_text(raw_special.get("title"))

    if not title:
        return None

    return {
        "title": title,
        "description": clean_text(raw_special.get("description")),
        "price": clean_text(raw_special.get("price")),
    }


def create_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_template(
    environment: Environment,
    template_name: str,
    output_name: str,
    context: dict[str, Any],
) -> None:
    template = environment.get_template(template_name)
    html = template.render(**context)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / output_name
    temporary_file = output_file.with_suffix(".html.tmp")

    temporary_file.write_text(html, encoding="utf-8")
    temporary_file.replace(output_file)

    log(f"Erzeugt: {output_file}")


def build_fallback_context(
    fallback_key: str,
    page_title: str,
) -> dict[str, Any]:
    fallback = FALLBACKS[fallback_key]

    return {
        "page_title": page_title,
        "is_fallback": True,
        "fallback": fallback,
    }


def write_status(status: dict[str, Any]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "status": "ok",
        "generated_at": datetime.now().astimezone().isoformat(),
        "slides": status,
    }

    temporary_file = STATUS_FILE.with_suffix(".json.tmp")

    temporary_file.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_file.replace(STATUS_FILE)

    log(f"Status gespeichert: {STATUS_FILE}")


def main() -> int:
    today = date.today()
    tomorrow = today + timedelta(days=1)

    data = load_menu_data()
    days = get_valid_days(data)
    weekly_special = get_weekly_special(data)

    environment = create_environment()

    status: dict[str, Any] = {}

    # ---------------------------------------------------------
    # 1. Wochenübersicht
    # ---------------------------------------------------------

    if days:
        period = data.get("period", {}) if data else {}

        period_start = parse_iso_date(period.get("start_date"))
        period_end = parse_iso_date(period.get("end_date"))

        render_template(
            environment,
            OVERVIEW_TEMPLATE,
            "uebersicht.html",
            {
                "page_title": "Mittagsmenü",
                "is_fallback": False,
                "period_text": format_period(period_start, period_end),
                "days": days,
            },
        )

        status["overview"] = {
            "available": True,
            "fallback": False,
            "output": "pages/menue/uebersicht.html",
        }
    else:
        render_template(
            environment,
            OVERVIEW_TEMPLATE,
            "uebersicht.html",
            build_fallback_context(
                "overview",
                "Mittagsmenü",
            ),
        )

        status["overview"] = {
            "available": False,
            "fallback": True,
            "output": "pages/menue/uebersicht.html",
        }

    # ---------------------------------------------------------
    # 2. Wochenschmankerl
    # ---------------------------------------------------------

    if weekly_special:
        render_template(
            environment,
            WEEKLY_TEMPLATE,
            "wochenschmankerl.html",
            {
                "page_title": "Wochenschmankerl",
                "is_fallback": False,
                "period_text": format_period(
                    parse_iso_date(data.get("period", {}).get("start_date")),
                    parse_iso_date(data.get("period", {}).get("end_date")),
                ),
                "special": weekly_special,
            },
        )

        status["weekly"] = {
            "available": True,
            "fallback": False,
            "output": "pages/menue/wochenschmankerl.html",
        }
    else:
        render_template(
            environment,
            WEEKLY_TEMPLATE,
            "wochenschmankerl.html",
            build_fallback_context(
                "weekly",
                "Wochenschmankerl",
            ),
        )

        status["weekly"] = {
            "available": False,
            "fallback": True,
            "output": "pages/menue/wochenschmankerl.html",
        }

    # ---------------------------------------------------------
    # 3. Heutiges Mittagsmenü
    # ---------------------------------------------------------

    today_menu = find_menu_for_date(days, today)

    if today_menu:
        render_template(
            environment,
            DAY_TEMPLATE,
            "heute.html",
            {
                "page_title": "Das heutige Mittagsmenü",
                "is_fallback": False,
                "menu": today_menu,
                "time_mode": "today",
            },
        )

        status["today"] = {
            "available": True,
            "fallback": False,
            "date": today.isoformat(),
            "valid_from": "00:00",
            "valid_until": "13:00",
            "output": "pages/menue/heute.html",
        }
    else:
        render_template(
            environment,
            DAY_TEMPLATE,
            "heute.html",
            {
                **build_fallback_context(
                    "today",
                    "Das heutige Mittagsmenü",
                ),
                "time_mode": "today",
            },
        )

        status["today"] = {
            "available": False,
            "fallback": True,
            "date": today.isoformat(),
            "valid_from": "00:00",
            "valid_until": "13:00",
            "output": "pages/menue/heute.html",
        }

    # ---------------------------------------------------------
    # 4. Morgiges Mittagsmenü
    # ---------------------------------------------------------

    tomorrow_menu = find_menu_for_date(days, tomorrow)

    if tomorrow_menu:
        render_template(
            environment,
            DAY_TEMPLATE,
            "morgen.html",
            {
                "page_title": "Das morgige Mittagsmenü",
                "is_fallback": False,
                "menu": tomorrow_menu,
                "time_mode": "tomorrow",
            },
        )

        status["tomorrow"] = {
            "available": True,
            "fallback": False,
            "date": tomorrow.isoformat(),
            "valid_from": "13:00",
            "valid_until": "23:59",
            "output": "pages/menue/morgen.html",
        }
    else:
        render_template(
            environment,
            DAY_TEMPLATE,
            "morgen.html",
            {
                **build_fallback_context(
                    "tomorrow",
                    "Das morgige Mittagsmenü",
                ),
                "time_mode": "tomorrow",
            },
        )

        status["tomorrow"] = {
            "available": False,
            "fallback": True,
            "date": tomorrow.isoformat(),
            "valid_from": "13:00",
            "valid_until": "23:59",
            "output": "pages/menue/morgen.html",
        }

    write_status(status)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        log(f"Export fehlgeschlagen: {exc}")
        sys.exit(1)
