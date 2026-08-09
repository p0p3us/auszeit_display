#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urljoin
import email.utils
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

BASE_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()

SOURCES_FILE = BASE_DIR / "data" / "news_sources.json"
OUTPUT_FILE = BASE_DIR / "data" / "news.json"
NEWS_IMAGE_DIR = BASE_DIR / "resources" / "news"

ITEMS_PER_SOURCE = 2
TIMEOUT_SECONDS = 15

DEFAULT_IMAGE_PATH = "/auszeit-display/resources/images/news.png"


def load_sources() -> list[dict]:
    if not SOURCES_FILE.exists():
        raise FileNotFoundError(f"News-Quellen fehlen: {SOURCES_FILE}")

    with SOURCES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def first_child_text(element: ET.Element, names: list[str]) -> str:
    for child in list(element):
        if local_name(child.tag) in names and child.text:
            return child.text
    return ""


def first_child(element: ET.Element, names: list[str]) -> ET.Element | None:
    for child in list(element):
        if local_name(child.tag) in names:
            return child
    return None


def all_descendants_by_name(element: ET.Element, name: str) -> list[ET.Element]:
    return [node for node in element.iter() if local_name(node.tag) == name]


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.strip().split())


def parse_date(value: str | None) -> str:
    if not value:
        return ""

    value = clean_text(value)

    # ISO-Format, z. B. 2026-07-12T06:01:33+02:00
    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value)
            return parsed.strftime("%d.%m.%Y %H:%M")
    except Exception:
        pass

    # Klassisches RSS pubDate-Format
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return value


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AuszeitDisplay/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()

def get_attribute_by_local_name(element: ET.Element, attribute_name: str) -> str:
    for key, value in element.attrib.items():
        if key == attribute_name:
            return value

        if "}" in key and key.split("}", 1)[1] == attribute_name:
            return value

    return ""


def extract_article_url(item: ET.Element) -> str:
    rdf_about = get_attribute_by_local_name(item, "about")
    if rdf_about:
        return clean_text(rdf_about)

    return extract_link(item)


def pick_from_srcset(srcset: str) -> str:
    if not srcset:
        return ""

    srcset = html.unescape(srcset)

    # ORF verwendet in Bild-URLs Kommas, z. B.:
    # crops/w=640,h=256,q=70,r=2/...
    # Deshalb darf hier NICHT einfach mit split(",") getrennt werden.
    image_urls = re.findall(
        r"""https?://[^\s"']+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"']*)?""",
        srcset,
        flags=re.IGNORECASE,
    )

    if image_urls:
        # Ersten Treffer nehmen, weil ORF meistens zuerst die passende Desktop-Variante liefert.
        return image_urls[0]

    # Fallback für relative URLs ohne Domain
    relative_urls = re.findall(
        r"""(/[^\s"']+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"']*)?)""",
        srcset,
        flags=re.IGNORECASE,
    )

    if relative_urls:
        return relative_urls[0]

    return ""


def find_picture_image_url_from_html(page_html: str, base_url: str) -> str:
    if not page_html:
        return ""

    # 1. <picture>-Blöcke durchsuchen
    picture_blocks = re.findall(
        r"<picture\b[^>]*>(.*?)</picture>",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for block in picture_blocks:
        # normale und lazy-loaded srcsets
        srcset_matches = re.findall(
            r"""<source\b[^>]*(?:srcset|data-srcset)=["']([^"']+)["']""",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for srcset in reversed(srcset_matches):
            candidate = pick_from_srcset(srcset)
            if candidate:
                return urljoin(base_url, html.unescape(candidate))

        # normale und lazy-loaded img-Attribute
        # img srcset bevorzugen
        img_srcset_matches = re.findall(
            r"""<img\b[^>]*(?:srcset|data-srcset)=["']([^"']+)["']""",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for srcset in img_srcset_matches:
            candidate = pick_from_srcset(srcset)
            if candidate:
                return urljoin(base_url, html.unescape(candidate))

        # normales img src als Fallback
        img_matches = re.findall(
            r"""<img\b[^>]*(?:src|data-src)=["']([^"']+)["']""",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for candidate in img_matches:
            if candidate:
                return urljoin(base_url, html.unescape(candidate))

    # 2. og:image, egal in welcher Attribut-Reihenfolge
    og_match = re.search(
        r"""<meta\b(?=[^>]*property=["']og:image["'])(?=[^>]*content=["']([^"']+)["'])[^>]*>""",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if og_match:
        return urljoin(base_url, html.unescape(og_match.group(1)))

    # 3. twitter:image
    twitter_match = re.search(
        r"""<meta\b(?=[^>]*(?:name|property)=["']twitter:image["'])(?=[^>]*content=["']([^"']+)["'])[^>]*>""",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if twitter_match:
        return urljoin(base_url, html.unescape(twitter_match.group(1)))

    # 4. JSON-LD / eingebettete Bild-URLs
    json_image_match = re.search(
        r""""image"\s*:\s*(?:\[\s*)?["']([^"']+\.(?:jpg|jpeg|png|webp)(?:\?[^"']*)?)["']""",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if json_image_match:
        return urljoin(base_url, html.unescape(json_image_match.group(1)))

    # 5. letzter Fallback: irgendeine Bilddatei aus der HTML-Seite
    generic_image_match = re.search(
        r"""https?://[^"']+\.(?:jpg|jpeg|png|webp)(?:\?[^"']*)?""",
        page_html,
        flags=re.IGNORECASE,
    )

    if generic_image_match:
        return html.unescape(generic_image_match.group(0))

    return ""

def find_image_url_from_article_page(article_url: str) -> str:
    if not article_url:
        print("WARNUNG: Keine Artikel-URL für Bildsuche vorhanden.")
        return ""

    try:
        page_data = fetch_bytes(article_url)
        page_html = page_data.decode("utf-8", errors="replace")

        image_url = find_picture_image_url_from_html(page_html, article_url)

        if not image_url:
            print(f"WARNUNG: Kein Bild auf Artikelseite gefunden: {article_url}")

        return image_url

    except Exception as error:
        print(f"WARNUNG: Artikelseite konnte nicht geladen werden: {article_url} -> {error}")
        return ""

def extract_link(item: ET.Element) -> str:
    # RSS
    link = clean_text(first_child_text(item, ["link"]))
    if link:
        return link

    # Atom
    link_element = first_child(item, ["link"])
    if link_element is not None:
        href = link_element.attrib.get("href", "")
        if href:
            return clean_text(href)

    return ""


def find_image_url(item: ET.Element) -> str:
    # media:content / media:thumbnail oder ähnliche Namespace-Varianten
    for node in item.iter():
        node_name = local_name(node.tag)

        if node_name in ["content", "thumbnail"]:
            url = node.attrib.get("url", "")
            medium = node.attrib.get("medium", "")
            mime_type = node.attrib.get("type", "")

            if url and (
                medium == "image"
                or mime_type.startswith("image/")
                or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            ):
                return url

    # enclosure
    enclosure = first_child(item, ["enclosure"])
    if enclosure is not None:
        url = enclosure.attrib.get("url", "")
        mime_type = enclosure.attrib.get("type", "")
        if url and (mime_type.startswith("image/") or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
            return url

    # Bild aus description / content extrahieren
    possible_html = " ".join(
        [
            first_child_text(item, ["description"]),
            first_child_text(item, ["encoded"]),
            first_child_text(item, ["summary"]),
            first_child_text(item, ["content"]),
        ]
    )

    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', possible_html)
    if match:
        return match.group(1)

    return ""


def image_extension_from_url(url: str) -> str:
    path = urlparse(url).path.lower()

    if path.endswith(".png"):
        return ".png"
    if path.endswith(".webp"):
        return ".webp"
    if path.endswith(".jpeg"):
        return ".jpg"
    if path.endswith(".jpg"):
        return ".jpg"

    return ".jpg"


def download_image(url: str, filename_stem: str) -> str:
    if not url:
        return DEFAULT_IMAGE_PATH

    try:
        NEWS_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        extension = image_extension_from_url(url)
        target_file = NEWS_IMAGE_DIR / f"{filename_stem}{extension}"

        image_data = fetch_bytes(url)
        target_file.write_bytes(image_data)

        return f"/auszeit-display/resources/news/{target_file.name}"
    except Exception:
        return DEFAULT_IMAGE_PATH


def extract_items(root: ET.Element) -> list[ET.Element]:
    # RSS 2.0
    rss_items = all_descendants_by_name(root, "item")
    if rss_items:
        return rss_items

    # Atom
    atom_entries = all_descendants_by_name(root, "entry")
    if atom_entries:
        return atom_entries

    return []


def parse_feed(source: dict) -> tuple[list[dict], str | None]:
    source_key = source.get("key", "quelle")
    source_name = source.get("name", "Unbekannt")
    url = source.get("url", "")

    if not url:
        return [], f"{source_name}: keine URL"

    try:
        xml_data = fetch_bytes(url)
        root = ET.fromstring(xml_data)

        raw_items = extract_items(root)

        if not raw_items:
            return [], f"{source_name}: keine Items gefunden"

        items = []

        for raw_item in raw_items:
            if len(items) >= ITEMS_PER_SOURCE:
                break

            index = len(items) + 1

            title = clean_text(first_child_text(raw_item, ["title"]))

            description = clean_text(
                first_child_text(raw_item, ["description", "summary", "encoded", "content"])
            )

            # Items ohne Beschreibung überspringen.
            # Besonders beim Sport-Feed gibt es sonst Einträge ohne brauchbaren Meldungstext.
            if not title or not description:
                continue

            link = extract_article_url(raw_item)

            pub_date = parse_date(
                first_child_text(raw_item, ["pubDate", "published", "updated", "date"])
            )

            page_slug = f"{source_key}-{index}"

            image_url = find_image_url(raw_item)

            # Sport-Bilder liegen häufig nicht direkt im RSS-Item,
            # sondern auf der Artikelseite. Deshalb bei Sport immer zusätzlich prüfen,
            # wenn das RSS-Item kein Bild liefert.
            if not image_url and source_key == "sport":
                article_url = extract_article_url(raw_item)
                image_url = find_image_url_from_article_page(article_url)

            image_path = download_image(image_url, page_slug)

            items.append(
                {
                    "source_key": source_key,
                    "source": source_name,
                    "index": index,
                    "page": f"{page_slug}.html",
                    "title": title,
                    "description": description,
                    "link": link,
                    "published": pub_date,
                    "image_url": image_url,
                    "image_path": image_path,
                }
            )

        return items, None

    except Exception as error:
        return [], f"{source_name}: {error}"


def main() -> int:
    sources = load_sources()
    all_items = []
    errors = []
    source_counts = {}

    for source in sources:
        source_name = source.get("name", "Unbekannt")
        items, error = parse_feed(source)

        all_items.extend(items)
        source_counts[source_name] = len(items)

        if error:
            errors.append(error)

    output = {
        "updated": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "items_per_source": ITEMS_PER_SOURCE,
        "source_counts": source_counts,
        "sources": sources,
        "items": all_items,
        "errors": errors,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_expected = len(sources) * ITEMS_PER_SOURCE

    print(f"OK: {OUTPUT_FILE}")
    print(f"Meldungen: {len(all_items)} von {total_expected}")

    for source_name, count in source_counts.items():
        print(f"- {source_name}: {count}")

    if errors:
        print("WARNUNGEN:")
        for error in errors:
            print(f"- {error}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        raise SystemExit(1)
