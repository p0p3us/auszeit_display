import json
from pathlib import Path

BASE_DIR = Path("/home/pi/auszeit_display")
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "display_state.json"

DEFAULT_STATE = {
    "active_page": "system/default.html"
}


def get_display_state() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not STATE_FILE.exists():
        save_display_state(DEFAULT_STATE)
        return DEFAULT_STATE.copy()

    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)
    except (json.JSONDecodeError, OSError):
        state = DEFAULT_STATE.copy()
        save_display_state(state)

    if "active_page" not in state:
        state["active_page"] = DEFAULT_STATE["active_page"]
        save_display_state(state)

    return state


def save_display_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)


def set_active_page(page_path: str) -> None:
    state = get_display_state()
    state["active_page"] = page_path
    save_display_state(state)


def get_active_page() -> str:
    state = get_display_state()
    return state.get("active_page", DEFAULT_STATE["active_page"])
