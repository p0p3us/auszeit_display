#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


PROJECT_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()

INDEX_URL = (
    "https://populorum.eu/"
    "menu_admin/data/menus/index.json"
)

OUTPUT_FILE = PROJECT_DIR / "data" / "menue.json"
SOURCE_FILE = PROJECT_DIR / "data" / "menue_source.json"

REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux aarch64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 "
    "Auszeit-Digital-Signage/2.0"
)

WEEKDAYS = {
    "dienstag": {
        "label": "Dienstag",
        "weekday_number": 1,
    },
    "mittwoch": {
        "label": "Mittwoch",
        "weekday_number": 2,
    },
    "donnerstag": {
        "label": "Donnerstag",
        "weekday_number": 3,
    },
    "freitag": {
        "label": "Freitag",
        "weekday_number": 4,
    },
}


def log(message: str) -> None:
    print(f"[fetch_menue] {message}", flush=True)


def create_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "de-AT,de;q=0.9",
        }
    )

    return session


def fetch_json(
    session: requests.Session,
    url: str,
) -> dict[str, Any]:
    log(f"Lade JSON: {url}")

    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except requests.JSONDecodeError as exc:
        raise ValueError(
            f"Ungültige JSON-Antwort von {url}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            f"JSON-Wurzel ist kein Objekt: {url}"
        )

    return payload


def parse_iso_date(
    value: Any,
    field_name: str,
) -> date:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Datumsfeld '{field_name}' fehlt oder ist leer."
        )

    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(
            f"Ungültiges Datum in '{field_name}': {value}"
        ) from exc


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).replace("\u00a0", " ").strip()


def clean_price(value: Any) -> str:
    """
    Wandelt beispielsweise

        € 9,90
        EUR 9,90
        9.90 €

    in

        9,90

    um. Das Eurozeichen wird im HTML-Template ergänzt.
    """

    text = clean_text(value)

    if not text:
        return ""

    text = re.sub(
        r"(?i)\bEUR\b",
        "",
        text,
    )

    text = text.replace("€", "")
    text = re.sub(r"\s+", " ", text).strip()

    match = re.search(
        r"(\d{1,4}(?:[.,]\d{2}))",
        text,
    )

    if match:
        return match.group(1).replace(".", ",")

    return text


def validate_filename(value: Any) -> str:
    filename = clean_text(value)

    if not filename:
        raise ValueError(
            "Ein Indexeintrag enthält keinen Dateinamen."
        )

    # Nur der reine Dateiname darf verwendet werden.
    # Verzeichniswechsel wie ../ werden damit ausgeschlossen.
    safe_filename = Path(filename).name

    if safe_filename != filename:
        raise ValueError(
            f"Unzulässiger Dateiname im Index: {filename}"
        )

    if not safe_filename.lower().endswith(".json"):
        raise ValueError(
            f"Menüdatei ist keine JSON-Datei: {filename}"
        )

    return safe_filename


def normalize_index_entries(
    index_data: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_menus = index_data.get("menus")

    if not isinstance(raw_menus, list):
        raise ValueError(
            "Die Indexdatei enthält keine gültige 'menus'-Liste."
        )

    entries: list[dict[str, Any]] = []

    for position, raw_entry in enumerate(raw_menus, start=1):
        if not isinstance(raw_entry, dict):
            log(
                f"Indexeintrag {position} wird ignoriert: "
                "kein JSON-Objekt."
            )
            continue

        try:
            filename = validate_filename(
                raw_entry.get("file")
            )

            valid_from = parse_iso_date(
                raw_entry.get("valid_from"),
                "valid_from",
            )

            valid_until = parse_iso_date(
                raw_entry.get("valid_until"),
                "valid_until",
            )

            if valid_until < valid_from:
                raise ValueError(
                    "valid_until liegt vor valid_from."
                )

        except ValueError as exc:
            log(
                f"Indexeintrag {position} wird ignoriert: {exc}"
            )
            continue

        entries.append(
            {
                "file": filename,
                "valid_from": valid_from,
                "valid_until": valid_until,
            }
        )

    entries.sort(
        key=lambda item: (
            item["valid_from"],
            item["valid_until"],
            item["file"],
        )
    )

    return entries


def select_menu_entry(
    entries: list[dict[str, Any]],
    reference_date: date,
) -> dict[str, Any] | None:
    """
    Auswahlreihenfolge:

    1. Menü, dessen Zeitraum den heutigen Tag enthält.
    2. Menü mit dem nächstmöglichen zukünftigen Beginn.
    3. Kein Menü, wenn ausschließlich vergangene Einträge bestehen.
    """

    current_entries = [
        entry
        for entry in entries
        if (
            entry["valid_from"]
            <= reference_date
            <= entry["valid_until"]
        )
    ]

    if current_entries:
        current_entries.sort(
            key=lambda item: (
                item["valid_from"],
                item["file"],
            ),
            reverse=True,
        )

        return current_entries[0]

    future_entries = [
        entry
        for entry in entries
        if entry["valid_from"] > reference_date
    ]

    if future_entries:
        future_entries.sort(
            key=lambda item: (
                item["valid_from"],
                item["file"],
            )
        )

        return future_entries[0]

    return None


def find_date_in_period(
    valid_from: date,
    valid_to: date,
    weekday_number: int,
) -> date | None:
    current = valid_from

    while current <= valid_to:
        if current.weekday() == weekday_number:
            return current

        current += timedelta(days=1)

    return None


def normalize_regular_menu(
    raw_menu: Any,
) -> dict[str, str] | None:
    if not isinstance(raw_menu, dict):
        return None

    title = clean_text(raw_menu.get("title"))

    if not title:
        return None

    return {
        "soup": clean_text(raw_menu.get("soup"))
        or "Tagessuppe",
        "title": title,
        "description": clean_text(raw_menu.get("side")),
        "price": clean_price(raw_menu.get("price")),
    }


def normalize_friday(
    raw_friday: Any,
) -> tuple[
    dict[str, str] | None,
    list[dict[str, str]],
]:
    if not isinstance(raw_friday, dict):
        return None, []

    # Neues Format mit menu_1 und menu_2.
    if "menu_1" in raw_friday or "menu_2" in raw_friday:
        primary = normalize_regular_menu(
            raw_friday.get("menu_1")
        )

        alternatives: list[dict[str, str]] = []

        raw_menu_2 = raw_friday.get("menu_2")

        if (
            isinstance(raw_menu_2, dict)
            and raw_menu_2.get("enabled") is True
        ):
            menu_2 = normalize_regular_menu(raw_menu_2)

            if menu_2:
                alternatives.append(menu_2)

        return primary, alternatives

    # Rückfall, falls Freitag irgendwann wie die anderen Tage
    # direkt gespeichert wird.
    return normalize_regular_menu(raw_friday), []


def build_days(
    menu_data: dict[str, Any],
    valid_from: date,
    valid_to: date,
) -> list[dict[str, Any]]:
    raw_weekdays = menu_data.get("weekdays")

    if not isinstance(raw_weekdays, dict):
        raise ValueError(
            "Die Menüdatei enthält kein gültiges "
            "'weekdays'-Objekt."
        )

    days: list[dict[str, Any]] = []

    for key, config in WEEKDAYS.items():
        menu_date = find_date_in_period(
            valid_from,
            valid_to,
            config["weekday_number"],
        )

        if menu_date is None:
            log(
                f"{config['label']} liegt nicht im "
                "angegebenen Gültigkeitszeitraum."
            )
            continue

        raw_day = raw_weekdays.get(key)

        alternatives: list[dict[str, str]] = []

        if key == "freitag":
            normalized_menu, alternatives = (
                normalize_friday(raw_day)
            )
        else:
            normalized_menu = normalize_regular_menu(
                raw_day
            )

        if normalized_menu is None:
            log(
                f"Für {config['label']} sind keine "
                "vollständigen Menüdaten vorhanden."
            )
            continue

        entry: dict[str, Any] = {
            "weekday": config["label"],
            "date": menu_date.isoformat(),
            "soup": normalized_menu["soup"],
            "title": normalized_menu["title"],
            "description": normalized_menu[
                "description"
            ],
            "price": normalized_menu["price"],
        }

        # Die bisherigen Templates verwenden weiterhin das
        # erste Freitag-Menü. Ein optionales zweites Menü wird
        # aber bereits strukturiert mitgespeichert.
        if alternatives:
            entry["alternatives"] = alternatives

        days.append(entry)

    return days


def normalize_weekly_special(menu_data: dict[str, Any]) -> dict[str, Any] | None:
    raw_special = menu_data.get("weekly_special")

    if not isinstance(raw_special, dict):
        return None

    if raw_special.get("enabled") is not True:
        return None

    title = clean_text(raw_special.get("title"))

    if not title:
        log(
            "Wochenschmankerl ist aktiviert, "
            "enthält aber keinen Titel."
        )
        return None

    return {
        "title": title,
        "description": clean_text(raw_special.get("side")),
        "price": clean_price(raw_special.get("price")),
    }


def validate_menu_period(
    menu_data: dict[str, Any],
    selected_entry: dict[str, Any],
) -> tuple[date, date]:
    valid_from = parse_iso_date(
        menu_data.get("valid_from"),
        "valid_from",
    )

    # Menüdatei verwendet valid_to.
    # valid_until wird zusätzlich toleriert.
    raw_valid_to = menu_data.get("valid_to")

    if raw_valid_to is None:
        raw_valid_to = menu_data.get("valid_until")

    valid_to = parse_iso_date(
        raw_valid_to,
        "valid_to",
    )

    if valid_to < valid_from:
        raise ValueError(
            "Der Menüzeitraum endet vor seinem Beginn."
        )

    index_from = selected_entry["valid_from"]
    index_until = selected_entry["valid_until"]

    if (
        valid_from != index_from
        or valid_to != index_until
    ):
        log(
            "Hinweis: Zeitraum in Index und Menüdatei "
            "stimmt nicht exakt überein. "
            "Der Zeitraum aus der Menüdatei wird verwendet."
        )

    return valid_from, valid_to


def write_json_atomic(
    destination: Path,
    payload: dict[str, Any],
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    temporary_file.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_file.replace(destination)


def write_unavailable(
    reason: str,
    reference_date: date,
) -> None:
    payload = {
        "status": "unavailable",
        "generated_at": (
            datetime.now().astimezone().isoformat()
        ),
        "reference_date": reference_date.isoformat(),
        "reason": reason,
        "period": {
            "start_date": None,
            "end_date": None,
        },
        "service_time": "",
        "days": [],
        "has_weekly_special": False,
        "weekly_special": None,
    }

    write_json_atomic(
        OUTPUT_FILE,
        payload,
    )


def build_source_payload(
    index_data: dict[str, Any],
    selected_entry: dict[str, Any],
    selected_url: str,
    menu_data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "ok",
        "fetched_at": (
            datetime.now().astimezone().isoformat()
        ),
        "index_url": INDEX_URL,
        "index_generated_at": index_data.get(
            "generated_at"
        ),
        "selected": {
            "file": selected_entry["file"],
            "url": selected_url,
            "index_valid_from": (
                selected_entry["valid_from"].isoformat()
            ),
            "index_valid_until": (
                selected_entry["valid_until"].isoformat()
            ),
        },
        "source_data": menu_data,
    }


def main() -> int:
    reference_date = date.today()
    session = create_session()

    try:
        index_data = fetch_json(
            session,
            INDEX_URL,
        )

        entries = normalize_index_entries(index_data)

        if not entries:
            reason = (
                "Die Indexdatei enthält keine gültigen "
                "Menüeinträge."
            )
            log(reason)
            write_unavailable(reason, reference_date)
            return 0

        selected_entry = select_menu_entry(
            entries,
            reference_date,
        )

        if selected_entry is None:
            reason = (
                "Es wurde kein aktuelles oder zukünftiges "
                "Menü gefunden."
            )
            log(reason)
            write_unavailable(reason, reference_date)
            return 0

        selected_url = urljoin(
            INDEX_URL,
            selected_entry["file"],
        )

        # Zusätzliche Kontrolle, dass die Menüdatei auf
        # demselben Host wie die Indexdatei liegt.
        if (
            urlparse(selected_url).netloc
            != urlparse(INDEX_URL).netloc
        ):
            raise ValueError(
                "Menüdatei verweist auf einen "
                "unerlaubten externen Host."
            )

        menu_data = fetch_json(
            session,
            selected_url,
        )

        valid_from, valid_to = validate_menu_period(
            menu_data,
            selected_entry,
        )

        days = build_days(
            menu_data,
            valid_from,
            valid_to,
        )

        weekly_special = normalize_weekly_special(menu_data)

        payload = {
            "status": "ok",
            "generated_at": (
                datetime.now().astimezone().isoformat()
            ),
            "reference_date": reference_date.isoformat(),
            "source": {
                "index_url": INDEX_URL,
                "menu_url": selected_url,
                "filename": selected_entry["file"],
                "updated_at": menu_data.get(
                    "updated_at"
                ),
            },
            "period": {
                "start_date": valid_from.isoformat(),
                "end_date": valid_to.isoformat(),
            },
            "service_time": clean_text(
                menu_data.get("service_time")
            ),
            "days": days,
            "has_weekly_special": (
                weekly_special is not None
            ),
            "weekly_special": weekly_special,

            # Die Infoblöcke werden noch nicht auf den vier
            # Menüfolien angezeigt, bleiben aber verfügbar.
            "info_blocks": menu_data.get(
                "info_blocks",
                [],
            ),
        }

        source_payload = build_source_payload(
            index_data,
            selected_entry,
            selected_url,
            menu_data,
        )

        write_json_atomic(
            OUTPUT_FILE,
            payload,
        )

        write_json_atomic(
            SOURCE_FILE,
            source_payload,
        )

    except (
        requests.RequestException,
        OSError,
        ValueError,
    ) as exc:
        log(f"Abruf fehlgeschlagen: {exc}")

        # Bei einem vorübergehenden Netzwerkfehler bleibt eine
        # vorhandene letzte erfolgreiche Datei bestehen.
        # Dadurch werden nicht wegen eines kurzen Ausfalls alle
        # Menüfolien verworfen.
        if OUTPUT_FILE.exists():
            log(
                "Die zuletzt erfolgreich gespeicherte "
                "menue.json bleibt erhalten."
            )
            return 0

        write_unavailable(
            str(exc),
            reference_date,
        )
        return 0

    log(
        f"Ausgewählt: {selected_entry['file']} | "
        f"{valid_from.isoformat()} bis "
        f"{valid_to.isoformat()}"
    )

    log(
        f"{len(days)} reguläre Menütag(e) gespeichert."
    )

    if weekly_special:
        log(
            "Wochenschmankerl vorhanden: "
            f"{weekly_special['title']}"
        )
    else:
        log("Kein Wochenschmankerl aktiviert.")

    log(f"Menüdaten gespeichert: {OUTPUT_FILE}")
    log(f"Quelldaten gespeichert: {SOURCE_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
