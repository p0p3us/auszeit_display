from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from player.update_test import updater
from player.update_test.exercise import feed, package, run


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = updater.Store(self.temp.name)
        self.routes = package("one", "Version one")
        self.feed = feed(self.routes)
        self.url = self.feed.__enter__()
        self.addCleanup(self.feed.__exit__, None, None, None)
        self.client = updater.Downloader(self.url, allow_loopback_http=True)

    def install(self):
        self.store.update(self.client)
        return self.store.state()

    def change_manifest(self, mutate):
        latest = json.loads(self.routes["/latest.json"])
        name = "/" + latest["manifest_path"]
        manifest = json.loads(self.routes[name])
        mutate(manifest)
        self.routes[name] = json.dumps(manifest).encode()
        latest["manifest_sha256"] = updater.digest(self.routes[name])
        self.routes["/latest.json"] = json.dumps(latest).encode()

    def test_six_scenarios_on_real_local_http(self):
        run(Path(self.temp.name) / "exercise")

    def test_repeated_release_keeps_previous_and_verifies_disk(self):
        self.install()
        self.routes.clear()
        self.routes.update(package("two", "Version two"))
        previous = self.install()
        self.assertEqual(self.install(), previous)
        (self.store.releases / "two/content/auszeit-display/style.css").write_bytes(b"tampered")
        with self.assertRaises(updater.InvalidRelease):
            self.install()
        self.assertEqual(self.store.state(), previous)

    def test_bad_manifest_hash_preserves_active(self):
        before = self.install()
        self.routes["/releases/one/manifest.json"] += b" "
        with self.assertRaises(updater.InvalidRelease):
            self.install()
        self.assertEqual(self.store.state(), before)

    def test_low_space_preserves_active(self):
        before = self.install()
        self.routes.clear()
        self.routes.update(package("two", "Version two"))
        with patch.object(updater.shutil, "disk_usage") as usage:
            usage.return_value.free = 0
            with self.assertRaisesRegex(updater.InvalidRelease, "storage"):
                self.install()
        self.assertEqual(self.store.state(), before)

    def test_interruption_before_pointer_replace_leaves_old_release(self):
        before = self.install()
        self.routes.clear()
        self.routes.update(package("two", "Version two"))
        with patch.object(updater.os, "replace", side_effect=OSError("power loss simulation")):
            with self.assertRaises(OSError):
                self.install()
        self.assertEqual(updater.Store(self.temp.name).state(), before)
        self.assertEqual(self.install()["active"]["release_id"], "two")

    def test_concurrent_writer_is_rejected(self):
        with updater.lock(self.store.root):
            with self.assertRaises(OSError):
                self.install()
        self.assertIsNone(self.store.state()["active"])

    def test_unsafe_paths_rejected(self):
        manifest = json.loads(self.routes["/releases/one/manifest.json"])
        for name in ("../outside", "/absolute", "auszeit-display/../outside", "auszeit-display/%2e%2e/x",
                     "auszeit-display/a\\b", "auszeit-display/CON.txt", "auszeit-display/a?query", "auszeit-display/a."):
            changed = deepcopy(manifest)
            changed["files"][0]["path"] = name
            with self.subTest(name=name), self.assertRaises(updater.InvalidRelease):
                updater.validate_manifest(changed, "one")

    def test_invalid_playlist_and_duplicate_files_rejected(self):
        original = json.loads(self.routes["/releases/one/manifest.json"])
        for mutate in (lambda m: m["files"].append(m["files"][0]),
                       lambda m: m["playlist"][0].update(path="auszeit-display/missing.html"),
                       lambda m: m["playlist"][0].update(duration_seconds=True),
                       lambda m: m["playlist"][0].update(valid_from="2026-01-01T00:00:00"),
                       lambda m: m.update(schema_version=2)):
            changed = deepcopy(original)
            mutate(changed)
            with self.assertRaises(updater.InvalidRelease):
                updater.validate_manifest(changed, "one")

    def test_network_policy_requires_https_except_explicit_loopback(self):
        for url in ("http://example.com/", "http://127.0.0.1/", "file:///etc/passwd", "https://user:pw@example.com/"):
            with self.subTest(url=url), self.assertRaises(updater.InvalidRelease):
                updater.Downloader(url)
        with self.assertRaises(updater.InvalidRelease):
            updater.Downloader("http://192.168.178.55/", allow_loopback_http=True)
        with self.assertRaises(updater.InvalidRelease):
            updater.NoRedirect().redirect_request(None, None, 302, None, None, "https://example.com/")

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(updater.InvalidRelease):
            updater.read_json(b'{"schema_version":1,"schema_version":2}')
