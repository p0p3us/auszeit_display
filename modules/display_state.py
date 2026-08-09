import json
import os
import tempfile

from modules.settings import DATA_DIR, DEFAULT_PAGE

STATE_FILE = DATA_DIR / "display_state.json"

DEFAULT_STATE = {
    "active_page": DEFAULT_PAGE
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

    if not isinstance(state, dict):
        state = DEFAULT_STATE.copy()
        save_display_state(state)
        return state

    active_page = state.get("active_page")
    if not isinstance(active_page, str) or not active_page.strip():
        state["active_page"] = DEFAULT_STATE["active_page"]
        save_display_state(state)

    return state


def save_display_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA_DIR,
            prefix=f".{STATE_FILE.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = file.name
            json.dump(state, file, indent=2, ensure_ascii=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, STATE_FILE)
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


def set_active_page(page_path: str) -> None:
    state = get_display_state()
    state["active_page"] = page_path
    save_display_state(state)


def get_active_page() -> str:
    state = get_display_state()
    return state.get("active_page", DEFAULT_STATE["active_page"])
