from datetime import datetime, timezone
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from player.package_test.publish import publish
from player.package_test.server import PackageServer
from player.update_test.updater import InvalidRelease


class PackagePlaybackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        publish(self.temp.name, '1')
        self.server = PackageServer(('127.0.0.1', 0), self.temp.name)
        self.addCleanup(self.server.server_close)
        self.now = datetime(2026, 9, 23, tzinfo=timezone.utc)

    def state(self, seconds):
        return self.server.state(self.now, seconds)

    def test_switch_only_at_boundary_and_assets_are_pinned(self):
        first = self.state(0)['slide']
        publish(self.temp.name, '2')
        self.assertEqual(self.state(19)['slide'], first)
        second = self.state(20)['slide']
        self.assertEqual(second['id'], 'display-2:A')
        self.assertEqual(self.state(40)['slide']['id'], 'display-2:B')
        self.assertIn(first['path'], self.server.routes)
        self.assertIn(second['path'], self.server.routes)
        self.assertNotEqual(first['path'], second['path'])

    def test_failed_download_keeps_rotation(self):
        self.state(0)
        with self.assertRaises(InvalidRelease):
            publish(self.temp.name, 'broken')
        self.assertEqual(self.state(20)['slide']['id'], 'display-1:B')
        self.assertIsNone(self.state(21)['last_error'])

    def test_restart_loads_newest_without_feed(self):
        publish(self.temp.name, '2')
        self.assertEqual(self.state(0)['slide']['id'], 'display-2:A')
        with PackageServer(('127.0.0.1', 0), self.temp.name) as reopened:
            self.assertEqual(reopened.state(self.now, 0)['slide']['id'], 'display-2:A')

    def test_corrupt_active_at_start_uses_verified_previous(self):
        publish(self.temp.name, '2')
        path = self.server.store.releases / 'display-2/content/auszeit-display/a.html'
        path.write_bytes(b'corrupt')
        state = self.state(0)
        self.assertEqual(state['slide']['id'], 'display-1:A')
        self.assertIsNotNone(state['last_error'])

    def test_http_serves_only_verified_manifest_files(self):
        slide = self.state(0)['slide']
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)
        base = f'http://127.0.0.1:{self.server.server_port}'
        with urlopen(base + slide['path']) as response:
            self.assertIn('Inhaltsstand 1', response.read().decode())
        with urlopen(base + '/releases/display-1/content/auszeit-display/style.css') as response:
            self.assertTrue(response.headers['Content-Type'].startswith('text/css'))
        for path in ('/slides/a.html', '/releases/display-1/manifest.json',
                     '/releases/display-1/content/auszeit-display/../manifest.json',
                     '/releases/display-1/content/auszeit-display/%2e%2e/manifest.json'):
            with self.assertRaises(HTTPError) as caught:
                urlopen(base + path)
            self.assertEqual(caught.exception.code, 404)
