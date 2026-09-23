from pathlib import Path
import tempfile
import unittest

from scripts.generate_public_index import build_index


class PublicIndexTests(unittest.TestCase):
    def test_inventory_uses_actual_files_including_variable_event_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = ['index.html', 'news/index.html', 'news/help-1.html',
                     'weather/morgen-deluxe.html', 'termine/termin-7.html',
                     'menue/wochenschmankerl.html', 'static/css/test.css']
            for name in files:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            result = build_index(root)
            for name in files[1:-1]:
                self.assertIn(f'href="{name}"', result)
            self.assertNotIn('href="index.html"', result)
            self.assertNotIn('test.css', result)
            self.assertNotIn('termin-1.html', result)

    def test_inventory_escapes_labels_and_encodes_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'a & b.html').touch()
            result = build_index(root)
            self.assertIn('a &amp; b.html', result)
            self.assertIn('href="a%20%26%20b.html"', result)
