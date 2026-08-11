#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

PROJECT_DIR = Path(os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)).expanduser().resolve()
SOURCE_URL = "https://populorum.eu/menu_admin/data/termine/aktuell.json"
WEBINTERFACE_URL = "https://populorum.eu/menu_admin/"
OUTPUT_FILE = PROJECT_DIR / "data" / "termine.json"
IMAGE_DIR = PROJECT_DIR / "resources" / "termine"
REQUEST_TIMEOUT = 30
MAX_IMAGE_BYTES = 15 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


class PlainTextExtractor(HTMLParser):
    BLOCK_TAGS = {"br", "div", "p"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self.BLOCK_TAGS and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"div", "p"} and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line).strip()


def log(message: str) -> None:
    print(f"[fetch_termine] {message}", flush=True)


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Auszeit-Digital-Signage/2.0", "Accept-Language": "de-AT,de;q=0.9"})
    return session


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).replace("\u00a0", " ").strip()


def rich_text_to_plain(value: Any) -> str:
    parser = PlainTextExtractor()
    parser.feed(clean_text(value))
    parser.close()
    return parser.text()


def valid_date(value: Any) -> str:
    try:
        return date.fromisoformat(clean_text(value)).isoformat()
    except ValueError:
        return ""


def safe_image_url(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    url = urljoin(WEBINTERFACE_URL, text)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "populorum.eu":
        return ""
    if not parsed.path.startswith("/menu_admin/uploads/events/") or ".." in Path(parsed.path).parts:
        return ""
    return url


def normalize_events(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw_events = payload.get("next_events")
    if not isinstance(raw_events, list):
        raise ValueError("Die Terminquelle enthält keine gültige 'next_events'-Liste.")
    today = date.today().isoformat()
    events: list[dict[str, str]] = []
    for position, raw in enumerate(raw_events, start=1):
        if not isinstance(raw, dict):
            log(f"Eintrag {position} ignoriert: kein JSON-Objekt.")
            continue
        event_date = valid_date(raw.get("date"))
        title = clean_text(raw.get("title"))
        if not event_date or event_date < today or not title:
            log(f"Eintrag {position} ignoriert: Datum oder Titel ungültig.")
            continue
        events.append({
            "source": clean_text(raw.get("source")),
            "id": clean_text(raw.get("id") or raw.get("template_id")),
            "date": event_date, "time": clean_text(raw.get("time")), "title": title,
            "description": rich_text_to_plain(raw.get("description")), "price": clean_text(raw.get("price")),
            "reservation": clean_text(raw.get("reservation")), "image_url": safe_image_url(raw.get("image")),
            "image_path": "",
        })
    events.sort(key=lambda event: (event["date"], event["time"], event["title"]))
    return events


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as file:
            temporary_path = file.name
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def download_image(session: requests.Session, url: str, stem: str) -> str:
    if not url:
        return ""
    response = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    suffix = ALLOWED_IMAGE_TYPES.get(content_type)
    if suffix is None:
        raise ValueError(f"Nicht unterstützter Bildtyp: {content_type or 'unbekannt'}")
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    target = IMAGE_DIR / f"{stem}{suffix}"
    temporary = target.with_suffix(target.suffix + ".tmp")
    size = 0
    try:
        with temporary.open("wb") as file:
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_IMAGE_BYTES:
                    raise ValueError("Terminbild überschreitet 15 MB.")
                file.write(chunk)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return f"/auszeit-display/resources/termine/{target.name}"


def remove_unused_images(used_paths: set[str]) -> None:
    if not IMAGE_DIR.is_dir():
        return
    used_names = {Path(path).name for path in used_paths if path}
    for image in IMAGE_DIR.iterdir():
        if image.is_file() and image.name not in used_names:
            image.unlink()


def main() -> int:
    session = create_session()
    try:
        response = session.get(SOURCE_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("JSON-Wurzel ist kein Objekt.")
        events = normalize_events(payload)
        for index, event in enumerate(events, start=1):
            try:
                event["image_path"] = download_image(session, event["image_url"], f"event-{index}")
            except (requests.RequestException, OSError, ValueError) as exc:
                log(f"Bild für '{event['title']}' nicht übernommen: {exc}")
        atomic_write_json(OUTPUT_FILE, {"status": "ok", "source_url": SOURCE_URL, "generated_at": clean_text(payload.get("generated_at")), "events": events})
        remove_unused_images({event["image_path"] for event in events})
        log(f"{len(events)} Termine gespeichert: {OUTPUT_FILE}")
        return 0
    except (requests.RequestException, requests.JSONDecodeError, OSError, ValueError) as exc:
        log(f"Abruf fehlgeschlagen; letzter gültiger Stand bleibt erhalten: {exc}")
        return 0 if OUTPUT_FILE.exists() else 1


if __name__ == "__main__":
    sys.exit(main())
