import os
from pathlib import Path


DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", DEFAULT_BASE_DIR)
).expanduser().resolve()

PAGES_DIR = BASE_DIR / "pages"
UPLOAD_DIR = PAGES_DIR / "upload"
DATA_DIR = BASE_DIR / "data"
RESOURCES_DIR = BASE_DIR / "resources"
STATIC_DIR = BASE_DIR / "static"

DEFAULT_PAGE = "system/default.html"
