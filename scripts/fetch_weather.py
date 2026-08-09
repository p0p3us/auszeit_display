#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


BASE_DIR = Path(
    os.environ.get("AUSZEIT_DISPLAY_BASE_DIR", Path(__file__).resolve().parent.parent)
).expanduser().resolve()
CONFIG_FILE = BASE_DIR / "config" / "publish.env"
OUTPUT_FILE = BASE_DIR / "data" / "weather.json"


def load_env_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Config-Datei fehlt: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key:
            os.environ[key] = value


def get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Pflichtwert fehlt in config/publish.env: {name}")
    return value


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AuszeitDisplay/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="replace"))


def round_temp(value) -> int | None:
    if value is None:
        return None
    return round(float(value))


def wind_kmh_from_ms(value) -> int:
    return round(float(value or 0) * 3.6)


def get_local_datetime(timestamp: int, tz_offset_seconds: int) -> datetime:
    tz = timezone(timedelta(seconds=tz_offset_seconds))
    return datetime.fromtimestamp(timestamp, tz)


def weekday_long(dt: datetime) -> str:
    names = [
        "Montag",
        "Dienstag",
        "Mittwoch",
        "Donnerstag",
        "Freitag",
        "Samstag",
        "Sonntag",
    ]
    return names[dt.weekday()]


def weekday_short(dt: datetime) -> str:
    names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    return names[dt.weekday()]


def display_date(dt: datetime) -> str:
    return dt.strftime("%d.%m.")


def pick_representative_forecast(entries: list[dict], tz_offset_seconds: int) -> dict:
    """
    Nimmt bevorzugt den Eintrag rund um Mittag.
    Dadurch bekommen wir ein Tages-Icon und eine Beschreibung,
    die für eine Tagesfolie meist besser passt als Nachtwerte.
    """
    if not entries:
        return {}

    def distance_to_noon(entry: dict) -> int:
        dt = get_local_datetime(entry["dt"], tz_offset_seconds)
        return abs(dt.hour - 12)

    return sorted(entries, key=distance_to_noon)[0]


def dominant_description(entries: list[dict]) -> tuple[str, str, int | None, str]:
    """
    Liefert Beschreibung, Icon-Code, Wetter-ID und Hauptgruppe.
    Falls mehrere Wetterlagen vorkommen, gewinnt die häufigste Beschreibung.
    """
    descriptions = []

    for entry in entries:
        weather_items = entry.get("weather") or []
        if not weather_items:
            continue

        weather = weather_items[0]
        descriptions.append(
            (
                weather.get("description", ""),
                weather.get("icon", ""),
                weather.get("id"),
                weather.get("main", ""),
            )
        )

    if not descriptions:
        return "", "", None, ""

    counter = Counter(item[0] for item in descriptions)
    selected_description = counter.most_common(1)[0][0]

    for item in descriptions:
        if item[0] == selected_description:
            return item

    return descriptions[0]


def normalize_day(date_key: str, entries: list[dict], tz_offset_seconds: int) -> dict:
    if not entries:
        raise RuntimeError(f"Keine Forecast-Einträge für {date_key}")

    temps = []
    temp_mins = []
    temp_maxs = []
    humidities = []
    wind_values = []
    pop_values = []
    cloud_values = []

    for entry in entries:
        main = entry.get("main") or {}
        wind = entry.get("wind") or {}
        clouds = entry.get("clouds") or {}

        if "temp" in main:
            temps.append(float(main["temp"]))

        if "temp_min" in main:
            temp_mins.append(float(main["temp_min"]))

        if "temp_max" in main:
            temp_maxs.append(float(main["temp_max"]))

        if "humidity" in main:
            humidities.append(float(main["humidity"]))

        if "speed" in wind:
            wind_values.append(float(wind["speed"]))

        if "pop" in entry:
            pop_values.append(float(entry["pop"]))

        if "all" in clouds:
            cloud_values.append(float(clouds["all"]))

    representative = pick_representative_forecast(entries, tz_offset_seconds)
    rep_dt = get_local_datetime(representative["dt"], tz_offset_seconds)

    description, icon_code, weather_id, weather_main = dominant_description(entries)

    return {
        "date": date_key,
        "weekday": weekday_long(rep_dt),
        "weekday_short": weekday_short(rep_dt),
        "date_display": display_date(rep_dt),
        "timestamp": representative["dt"],

        "weather_id": weather_id,
        "weather_main": weather_main,
        "description": description,
        "icon_code": icon_code,

        "temp_min": round_temp(min(temp_mins or temps)),
        "temp_max": round_temp(max(temp_maxs or temps)),
        "temp_day": round_temp(representative.get("main", {}).get("temp")),
        "feels_like_day": round_temp(representative.get("main", {}).get("feels_like")),

        "rain_probability": round(max(pop_values or [0]) * 100),
        "wind_kmh": wind_kmh_from_ms(max(wind_values or [0])),
        "humidity": round(sum(humidities) / len(humidities)) if humidities else None,
        "clouds": round(sum(cloud_values) / len(cloud_values)) if cloud_values else None,

        "forecast_count": len(entries),
    }


def main() -> int:
    load_env_file(CONFIG_FILE)

    api_key = get_required_env("OPENWEATHER_API_KEY")
    lat = get_required_env("WEATHER_LAT")
    lon = get_required_env("WEATHER_LON")
    location_name = os.environ.get("WEATHER_LOCATION_NAME", "Eggendorf").strip() or "Eggendorf"

    query = urllib.parse.urlencode(
        {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
            "lang": "de",
        }
    )

    url = f"https://api.openweathermap.org/data/2.5/forecast?{query}"
    raw = fetch_json(url)

    forecast_list = raw.get("list") or []
    city = raw.get("city") or {}
    tz_offset_seconds = int(city.get("timezone", 7200))

    if not forecast_list:
        raise RuntimeError("Keine Forecast-Daten erhalten.")

    now_local = datetime.now(timezone(timedelta(seconds=tz_offset_seconds)))
    today_key = now_local.strftime("%Y-%m-%d")

    grouped: dict[str, list[dict]] = defaultdict(list)

    for entry in forecast_list:
        dt = get_local_datetime(entry["dt"], tz_offset_seconds)
        date_key = dt.strftime("%Y-%m-%d")

        # Heute überspringen, weil die Folien ab morgen beginnen sollen.
        if date_key <= today_key:
            continue

        grouped[date_key].append(entry)

    next_dates = sorted(grouped.keys())[:5]

    if len(next_dates) < 5:
        raise RuntimeError(f"Zu wenige Folgetage erhalten: {len(next_dates)}")

    five_days = [
        normalize_day(date_key, grouped[date_key], tz_offset_seconds)
        for date_key in next_dates
    ]

    tomorrow = five_days[0]

    output = {
        "source": "OpenWeatherMap 5 Day / 3 Hour Forecast API",
        "location": location_name,
        "api_location_name": city.get("name", ""),
        "country": city.get("country", ""),
        "lat": lat,
        "lon": lon,
        "timezone_offset_seconds": tz_offset_seconds,
        "updated": now_local.strftime("%d.%m.%Y %H:%M"),
        "tomorrow": tomorrow,
        "five_days": five_days,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wetterdaten geschrieben: {OUTPUT_FILE}")
    print(f"Ort: {location_name}")
    print(f"API-Ort: {city.get('name', '')}, {city.get('country', '')}")
    print(f"Morgen: {tomorrow['weekday']}, {tomorrow['date_display']} – {tomorrow['description']}")
    print(f"5-Tage-Vorschau: {len(five_days)} Tage")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        raise SystemExit(1)
