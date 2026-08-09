from pathlib import Path

from modules.settings import PAGES_DIR


def list_html_pages() -> list[dict]:
    pages = []

    if not PAGES_DIR.exists():
        return pages

    for file_path in sorted(PAGES_DIR.rglob("*.html")):
        relative_path = file_path.relative_to(PAGES_DIR).as_posix()
        pages.append({
            "path": relative_path,
            "name": file_path.name,
            "category": file_path.parent.name
        })

    return pages


def page_exists(page_path: str) -> bool:
    safe_path = Path(page_path)

    if safe_path.is_absolute() or ".." in safe_path.parts:
        return False

    full_path = PAGES_DIR / safe_path
    return full_path.exists() and full_path.is_file() and full_path.suffix == ".html"
