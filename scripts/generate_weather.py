#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()
DATA_FILE = BASE_DIR / "data" / "weather.json"
TEMPLATE_DIR = BASE_DIR / "templates" / "display_pages"
OUTPUT_DIR = BASE_DIR / "pages" / "weather"


ICON_MAP = {
    "01d": "clear-day.svg",
    "01n": "clear-night.svg",
    "02d": "few-clouds-day.svg",
    "02n": "few-clouds-night.svg",
    "03d": "clouds.svg",
    "03n": "clouds.svg",
    "04d": "clouds.svg",
    "04n": "clouds.svg",
    "09d": "shower-rain.svg",
    "09n": "shower-rain.svg",
    "10d": "rain-day.svg",
    "10n": "rain-night.svg",
    "11d": "thunderstorm.svg",
    "11n": "thunderstorm.svg",
    "13d": "snow.svg",
    "13n": "snow.svg",
    "50d": "mist.svg",
    "50n": "mist.svg",
}


def icon_path(icon_code: str) -> str:
    filename = ICON_MAP.get(icon_code, "clouds.svg")
    return f"/auszeit-display/resources/weather/icons/{filename}"

def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def terrace_score(day: dict) -> int:
    temp = float(day.get("temp_max") or 0)
    rain = float(day.get("rain_probability") or 0)
    wind = float(day.get("wind_kmh") or 0)

    score = 10

    if temp < 18:
        score -= 3
    elif temp < 22:
        score -= 1
    elif 23 <= temp <= 29:
        score += 1
    elif temp >= 33:
        score -= 1

    if rain >= 70:
        score -= 5
    elif rain >= 40:
        score -= 3
    elif rain >= 20:
        score -= 1

    if wind >= 35:
        score -= 2
    elif wind >= 25:
        score -= 1

    return round(clamp(score, 1, 10))


def umbrella_text(day: dict) -> str:
    rain = int(day.get("rain_probability") or 0)

    if rain >= 70:
        return "Mitnehmen. Sonst wird’s eine Demutübung."
    if rain >= 40:
        return "Riskant. Optimisten lassen ihn daheim."
    if rain >= 20:
        return "Kann, muss aber nicht. Österreichisches Klassikerwetter."
    return "Unnötig. Heute nur Deko."


def sunglasses_text(day: dict) -> str:
    clouds = int(day.get("clouds") or 0)
    rain = int(day.get("rain_probability") or 0)

    if rain >= 60:
        return "Eher nicht. Außer für den dramatischen Auftritt."
    if clouds <= 35:
        return "Ja. Ohne wirkt unvorbereitet."
    if clouds <= 70:
        return "Wahrscheinlich. Für den Fall der Fälle."
    return "Optional. Mehr Style als Notwendigkeit."


def jacket_text(day: dict) -> str:
    temp_min = int(day.get("temp_min") or 0)
    temp_max = int(day.get("temp_max") or 0)

    if temp_min <= 12:
        return "Ja. Früh wird’s sonst beleidigend frisch."
    if temp_max >= 26:
        return "Nein. Ballast mit Ärmeln."
    if temp_min <= 16:
        return "Leicht. Für die Morgen-Realität."
    return "Nein. Mut zur Bewegungsfreiheit."


def wind_text(day: dict) -> str:
    wind = int(day.get("wind_kmh") or 0)

    if wind >= 45:
        return "Frisur akut gefährdet."
    if wind >= 30:
        return "Frisur mit Eigenleben möglich."
    if wind >= 18:
        return "Spürbar, aber kein Drama."
    return "Harmlos. Haare bleiben verhandelbar."


def heat_text(day: dict) -> str:
    temp = int(day.get("temp_max") or 0)

    if temp >= 32:
        return "Kreislauf sagt: langsam machen."
    if temp >= 30:
        return "Warm. Getränke strategisch platzieren."
    if temp >= 24:
        return "Sehr brauchbar fürs draußen arbeiten."
    if temp >= 20:
        return "Okay. Kein Hochsommer-Geprahle."
    return "Frisch. Sommer macht Pause."


def deluxe_comment(day: dict) -> str:
    rain = int(day.get("rain_probability") or 0)
    temp = int(day.get("temp_max") or 0)
    wind = int(day.get("wind_kmh") or 0)

    sunglasses = "ja" if rain < 50 else "fraglich"
    jacket = "nein" if temp >= 24 else "vielleicht"
    excuses = "schwierig" if rain < 30 and wind < 30 and temp >= 20 else "möglich"

    return (
        f"Sonnenbrille {sunglasses}. Jacke {jacket}. "
        f"Ausreden fürs Drinnenbleiben: {excuses}."
    )


def enrich_deluxe(day: dict) -> dict:
    enriched = dict(day)

    score = terrace_score(day)

    enriched["terrace_score"] = score + 1 if score >= 5 else score - 1
    enriched["weather_index"] = f"{score},0"
    enriched["umbrella_text"] = umbrella_text(day)
    enriched["sunglasses_text"] = sunglasses_text(day)
    enriched["jacket_text"] = jacket_text(day)
    enriched["wind_text"] = wind_text(day)
    enriched["heat_text"] = heat_text(day)
    enriched["deluxe_comment"] = deluxe_comment(day)

    return enriched


def render_template(env: Environment, template_name: str, context: dict) -> str:
    template = env.get_template(template_name)
    html = template.render(**context).strip()

    if not html:
        raise RuntimeError(f"Template-Ausgabe ist leer: {template_name}")

    return html


def main() -> int:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Wetterdaten fehlen: {DATA_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    tomorrow = data["tomorrow"]
    five_days = data["five_days"]

    tomorrow["icon_path"] = icon_path(tomorrow.get("icon_code", ""))

    for day in five_days:
        day["icon_path"] = icon_path(day.get("icon_code", ""))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    base_context = {
        "location": data.get("location", "Eggendorf"),
        "updated": data.get("updated", ""),
    }

    tomorrow_html = render_template(
        env,
        "weather_tomorrow.html",
        {
            **base_context,
            "day": tomorrow,
        },
    )

    tomorrow_deluxe_html = render_template(
        env,
        "weather_tomorrow_deluxe.html",
        {
            **base_context,
            "day": enrich_deluxe(tomorrow),
        },
    )

    five_days_html = render_template(
        env,
        "weather_5days.html",
        {
            **base_context,
            "days": five_days,
        },
    )

    index_html = """<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Auszeit Wetter</title>
</head>
<body>
  <h1>Auszeit Wetter</h1>
  <ul>
    <li><a href="morgen.html">Wetter morgen</a></li>
    <li><a href="5tage.html">5-Tage-Vorschau</a></li>
    <li><a href="morgen-deluxe.html">Wetter morgen für Angeber</a></li>
  </ul>
</body>
</html>
"""

    (OUTPUT_DIR / "morgen.html").write_text(tomorrow_html, encoding="utf-8")
    (OUTPUT_DIR / "morgen-deluxe.html").write_text(tomorrow_deluxe_html, encoding="utf-8")
    (OUTPUT_DIR / "5tage.html").write_text(five_days_html, encoding="utf-8")
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

    print(f"Erstellt: {OUTPUT_DIR / 'morgen.html'}")
    print(f"Erstellt: {OUTPUT_DIR / '5tage.html'}")
    print(f"Erstellt: {OUTPUT_DIR / 'index.html'}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        raise SystemExit(1)
