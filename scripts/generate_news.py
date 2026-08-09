#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import json
import socket
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path("/home/pi/auszeit_display")

DATA_FILE = BASE_DIR / "data" / "news.json"
TEMPLATE_DIR = BASE_DIR / "templates" / "display_pages"
TEMPLATE_NAME = "news_item.html"
OUTPUT_DIR = BASE_DIR / "pages" / "news"

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


def load_news() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"News-Datei fehlt: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def render_news_index(items: list[dict], updated_text: str) -> str:
    links = "\n".join(
        f'<li><a href="{item.get("page", "#")}">{item.get("source", "")}: {item.get("title", "")}</a></li>'
        for item in items
    )

    if not links:
        links = "<li>Keine Meldungen vorhanden.</li>"

    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Auszeit News</title>
</head>
<body>
  <h1>Auszeit News</h1>
  <p>Aktualisiert: {updated_text}</p>
  <ul>
    {links}
  </ul>
</body>
</html>
"""


def main() -> int:
    now = datetime.now()
    news = load_news()
    items = news.get("items", [])
    updated_text = news.get("updated", now.strftime("%d.%m.%Y %H:%M"))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template(TEMPLATE_NAME)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Alte HTML-Seiten entfernen, damit keine veralteten Seiten liegen bleiben
    for old_file in OUTPUT_DIR.glob("*.html"):
        old_file.unlink()

    written_files = []

    for item in items:
        page_name = item.get("page")
        if not page_name:
            continue

        output_file = OUTPUT_DIR / page_name

        rendered_html = template.render(
            date_text=f"{now.day}. {MONTHS[now.month]} {now.year}",
            updated_text=updated_text,
            hostname=socket.gethostname(),
            source=item.get("source", ""),
            title=item.get("title", ""),
            description=item.get("description", ""),
            published=item.get("published", ""),
            image_path=item.get("image_path", "/auszeit-display/resources/images/news.png"),
            link=item.get("link", ""),
        )

        if not rendered_html.strip():
            raise ValueError(f"Template-Ausgabe ist leer für {output_file}")

        output_file.write_text(rendered_html, encoding="utf-8")
        written_files.append(output_file)

    index_file = OUTPUT_DIR / "index.html"
    index_html = render_news_index(items, updated_text)

    if not index_html.strip():
        raise ValueError("Index-Ausgabe ist leer.")

    index_file.write_text(index_html, encoding="utf-8")
    written_files.append(index_file)

    for file in written_files:
        print(f"OK: {file} ({file.stat().st_size} Bytes)")

    print(f"News-Seiten: {len(written_files) - 1}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        raise SystemExit(1)