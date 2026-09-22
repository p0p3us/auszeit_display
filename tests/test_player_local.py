import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

spec = importlib.util.spec_from_file_location("local_player", Path(__file__).resolve().parents[1] / "player/local_test/server.py")
player = importlib.util.module_from_spec(spec)
spec.loader.exec_module(player)


class PlaylistTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
        self.playlist = player.Playlist(player.demo_entries(self.now, "expiry"))

    def at(self, seconds):
        return self.playlist.select(self.now + timedelta(seconds=seconds), seconds)

    def test_rotation_skips_expired_and_honors_duration(self):
        for seconds, expected in [(0, "A"), (19, "A"), (20, "B"), (39, "B"), (40, "C"), (60, "A")]:
            self.assertEqual(self.at(seconds)["id"], expected)

    def test_expiry_interrupts_current_slide(self):
        for seconds in (0, 20, 40, 60):
            self.at(seconds)
        self.assertIsNone(self.at(65))
        self.assertIsNone(self.at(100))

    def test_empty_and_future_playlists(self):
        self.assertIsNone(player.Playlist([]).select(self.now, 0))
        self.playlist = player.Playlist([player.demo_entries(self.now, "expiry")[2]])
        self.assertIsNone(self.at(19))
        self.assertEqual(self.at(20)["id"], "B")

    def test_monotonic_duration_survives_wall_clock_adjustment(self):
        self.playlist = player.Playlist(player.demo_entries(self.now, "cycle"))
        self.assertEqual(self.playlist.select(self.now, 0)["id"], "A")
        self.assertEqual(self.playlist.select(self.now - timedelta(hours=1), 20)["id"], "B")

    def test_timezone_offsets_are_compared_as_instants(self):
        entry = player.demo_entries(self.now, "cycle")[0]
        entry["valid_from"] = "2026-09-22T14:00:00+02:00"
        entry["valid_until"] = "2026-09-22T14:01:00+02:00"
        self.playlist = player.Playlist([entry])
        self.assertIsNotNone(self.at(0))
        self.assertIsNone(self.at(60))

    def test_invalid_entries_rejected(self):
        for patch in ({"path": "/../secret"}, {"duration_seconds": True},
                      {"duration_seconds": 0}, {"valid_from": "2026-09-22T12:00:00"}):
            entry = player.demo_entries(self.now, "cycle")[0] | patch
            with self.assertRaises(ValueError):
                player.Playlist([entry])


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = player.TestServer(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_health_does_not_start_demo_and_routes_stay_local(self):
        with urlopen(self.base + "/healthz") as response:
            self.assertEqual(response.status, 200)
        self.assertIsNone(self.server.playlist)
        for path in ("/../server.py", "/%2e%2e/server.py", "/server.py"):
            with self.assertRaises(HTTPError) as caught:
                urlopen(self.base + path)
            self.assertEqual(caught.exception.code, 404)

    def test_api_and_slide_are_served_with_cache_disabled(self):
        import json
        with urlopen(self.base + "/api/state") as response:
            self.assertEqual(json.load(response)["slide"]["id"], "A")
        with urlopen(self.base + "/slides/b.html") as response:
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertIn("Folie B", response.read().decode())
