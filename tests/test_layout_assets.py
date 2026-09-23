from html.parser import HTMLParser
from pathlib import Path
import unittest

from layout_preview import build_cases


ROOT = Path(__file__).resolve().parents[1]


class StaticReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        value = attrs.get('src' if tag == 'script' else 'href', '')
        if value.startswith('/auszeit-display/static/'):
            self.paths.add(value.removeprefix('/auszeit-display/'))


class LayoutAssetTests(unittest.TestCase):
    def test_rendered_slide_fixtures_reference_existing_shared_assets(self):
        for name, source in build_cases().items():
            with self.subTest(slide=name):
                parser = StaticReferences()
                parser.feed(source)
                self.assertIn('static/js/display_layout.js', parser.paths)
                for path in parser.paths:
                    self.assertTrue((ROOT/path).is_file(), path)

    def test_both_exports_include_layout_runtime(self):
        for name in ('export_public.sh', 'export_namenstag_public.sh'):
            source = (ROOT/'scripts'/name).read_text(encoding='utf-8')
            self.assertIn('cp "$BASE_DIR/static/js/display_layout.js"', source)
