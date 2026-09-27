from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urljoin

from player.package_test.build_real_slide import build
from player.package_test.activate_real import activate
from player.package_test.server import PackageServer
from player.update_test.updater import InvalidRelease, Store


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        self.urls.extend(value for key, value in attrs if key in ('src', 'href'))


class RealSlideTests(unittest.TestCase):
    def test_reproducible_package_dependencies_and_playback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = build(root / 'feed')
            self.assertEqual(manifest, build(root / 'feed'))
            state = activate(root / 'feed', root / 'store')
            Store(root / 'store').verify(**state['active'])
            with PackageServer(('127.0.0.1', 0), root / 'store') as server:
                slide = server.state()['slide']
                self.assertEqual(slide['id'], manifest['release_id'] + ':weisheit')
                html = server.routes[slide['path']].read_text(encoding='utf-8')
                self.assertIn('Auszeit-Weisheit', html)
                parser = References()
                parser.feed(html)
                for reference in parser.urls:
                    path = urljoin(slide['path'], reference)
                    self.assertIn(path, server.routes)
                for path, local in server.routes.items():
                    if path.endswith('.css'):
                        css = local.read_text(encoding='utf-8')
                        self.assertNotIn('@import', css)
                        for reference in re.findall(r'url\([\'"]?([^\)\'\"]+)', css):
                            self.assertIn(urljoin(path, reference), server.routes)
                self.assertEqual(len(server.routes), 7)

    def test_damaged_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = build(root / 'feed')
            image = root / 'feed/releases' / manifest['release_id'] / 'content/auszeit-display/resources/images/logo.png'
            image.write_bytes(b'broken')
            with self.assertRaises(InvalidRelease):
                activate(root / 'feed', root / 'store')
            self.assertIsNone(Store(root / 'store').state()['active'])
