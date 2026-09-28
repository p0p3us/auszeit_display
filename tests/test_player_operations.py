import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from player.operations.run import cycle, post_status
from player.package_test.publish import publish
from player.package_test.server import PackageServer


class OperationsTests(unittest.TestCase):
    def test_failed_update_keeps_content_and_status_does_not_leak_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            publish(root / 'store', '1')
            def failure(url):
                raise OSError('SECRET must not appear')
            config = {'device_id': 'test', 'feed_url': 'https://example.org/feed/'}
            result = cycle(config, root / 'store', root / 'status', download_factory=failure, sampler=lambda _: {})
            self.assertEqual(result['content']['active']['release_id'], 'display-1')
            self.assertEqual(result['update_state'], 'failed')
            self.assertNotIn('SECRET', (root / 'status/status.json').read_text())

    def test_unconfigured_cycle_is_local_and_failed_report_preserves_last_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            status = root / 'status'
            status.mkdir()
            (status / 'status.json').write_text(json.dumps({'last_status_success': 'earlier'}))
            config = {'device_id': 'test', 'status_url': 'https://example.org/status.php', 'token_file': str(root / 'missing')}
            result = cycle(config, root / 'store', status, sampler=lambda _: {})
            self.assertEqual(result['update_state'], 'unconfigured')
            self.assertEqual(result['last_status_success'], 'earlier')
            self.assertEqual(result['report_error'], 'FileNotFoundError')

    def test_token_not_stored_in_status_and_ack_is_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'token').write_text('a' * 48)
            seen = []
            result = cycle({'device_id': 'test', 'status_url': 'https://example.org/status.php',
                            'token_file': str(root / 'token')}, root / 'store', root / 'status',
                           sampler=lambda _: {}, sender=lambda url, token, body: seen.append(token))
            self.assertEqual(seen, ['a' * 48])
            self.assertIsNotNone(result['last_status_success'])
            self.assertNotIn('a' * 48, (root / 'status/status.json').read_text())

    def test_status_rejects_plain_http_before_sending_token(self):
        with self.assertRaises(ValueError):
            post_status('http://example.org/status.php', 'a' * 48, {})

    def test_heartbeat_rejects_slide_origin_and_marks_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            with PackageServer(('127.0.0.1', 0), temporary) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                base = f'http://127.0.0.1:{server.server_port}'
                try:
                    body = b'{"state":"playing","slide_id":"demo:A"}'
                    with self.assertRaises(HTTPError) as error:
                        urlopen(Request(base + '/api/heartbeat', data=body, headers={'Origin': 'null'}))
                    self.assertEqual(error.exception.code, 403)
                    with urlopen(Request(base + '/api/heartbeat', data=body, headers={'Origin': base})) as response:
                        self.assertEqual(response.status, 200)
                    with urlopen(base + '/api/heartbeat') as response:
                        self.assertEqual(json.load(response)['state'], 'playing')
                    server.heartbeat['seen'] -= 31
                    with urlopen(base + '/api/heartbeat') as response:
                        self.assertEqual(json.load(response)['state'], 'unresponsive')
                finally:
                    server.shutdown()
                    thread.join()
