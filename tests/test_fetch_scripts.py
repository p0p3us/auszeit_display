import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests


PROJECT_DIR = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = PROJECT_DIR / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"test_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FetchScriptTests(unittest.TestCase):
    def test_weather_fetch_writes_five_valid_days(self):
        module = load_script("fetch_weather")
        now = datetime.now(timezone.utc)
        entries = []
        for day_offset in range(1, 6):
            forecast_time = (now + timedelta(days=day_offset)).replace(
                hour=12, minute=0, second=0, microsecond=0
            )
            entries.append(
                {
                    "dt": int(forecast_time.timestamp()),
                    "main": {
                        "temp": 20 + day_offset,
                        "temp_min": 15 + day_offset,
                        "temp_max": 22 + day_offset,
                        "feels_like": 20 + day_offset,
                        "humidity": 60,
                    },
                    "weather": [
                        {
                            "description": "leicht bewölkt",
                            "icon": "02d",
                            "id": 801,
                            "main": "Clouds",
                        }
                    ],
                    "wind": {"speed": 3},
                    "clouds": {"all": 30},
                    "pop": 0.2,
                }
            )

        raw_forecast = {
            "city": {"timezone": 0, "name": "Eggendorf", "country": "AT"},
            "list": entries,
        }

        with tempfile.TemporaryDirectory() as temporary_dir:
            output_file = Path(temporary_dir) / "weather.json"
            required = {
                "OPENWEATHER_API_KEY": "test-key",
                "WEATHER_LAT": "47.8",
                "WEATHER_LON": "16.3",
            }
            with (
                patch.object(module, "OUTPUT_FILE", output_file),
                patch.object(module, "load_env_file"),
                patch.object(module, "get_required_env", side_effect=required.__getitem__),
                patch.object(module, "fetch_json", return_value=raw_forecast),
            ):
                self.assertEqual(module.main(), 0)

            payload = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["five_days"]), 5)
            self.assertEqual(payload["tomorrow"], payload["five_days"][0])
            self.assertEqual(payload["location"], "Eggendorf")

    def test_news_fetch_collects_items_and_errors(self):
        module = load_script("fetch_news")
        sources = [
            {"key": "science", "name": "Wissenschaft", "url": "https://example.test/rss"},
            {"key": "sport", "name": "Sport", "url": "https://example.test/sport"},
        ]
        item = {
            "source_key": "science",
            "source": "Wissenschaft",
            "index": 1,
            "page": "science-1.html",
            "title": "Testmeldung",
            "description": "Testbeschreibung",
            "link": "https://example.test/article",
            "published": "09.08.2026 12:00",
            "image_url": "",
            "image_path": module.DEFAULT_IMAGE_PATH,
        }

        with tempfile.TemporaryDirectory() as temporary_dir:
            output_file = Path(temporary_dir) / "news.json"
            with (
                patch.object(module, "OUTPUT_FILE", output_file),
                patch.object(module, "load_sources", return_value=sources),
                patch.object(
                    module,
                    "parse_feed",
                    side_effect=[([item], None), ([], "Sport: Netzwerkfehler")],
                ),
            ):
                self.assertEqual(module.main(), 0)

            payload = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"], [item])
            self.assertEqual(payload["source_counts"], {"Wissenschaft": 1, "Sport": 0})
            self.assertEqual(payload["errors"], ["Sport: Netzwerkfehler"])

    def test_menu_fetch_keeps_last_good_file_on_network_error(self):
        module = load_script("fetch_menue")

        with tempfile.TemporaryDirectory() as temporary_dir:
            output_file = Path(temporary_dir) / "menue.json"
            previous_content = '{"status": "ok", "marker": "bestehend"}\n'
            output_file.write_text(previous_content, encoding="utf-8")

            with (
                patch.object(module, "OUTPUT_FILE", output_file),
                patch.object(module, "create_session", return_value=object()),
                patch.object(
                    module,
                    "fetch_json",
                    side_effect=requests.RequestException("simulierter Ausfall"),
                ),
            ):
                self.assertEqual(module.main(), 0)

            self.assertEqual(output_file.read_text(encoding="utf-8"), previous_content)


if __name__ == "__main__":
    unittest.main()
