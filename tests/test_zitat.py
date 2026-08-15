from datetime import date, datetime, timedelta
import html as html_lib
import importlib.util
from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "generate_zitat.py"
SPEC = importlib.util.spec_from_file_location("generate_zitat", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ZitatTests(unittest.TestCase):
    def test_source_contains_52_complete_zitate(self):
        zitate = MODULE.load_zitate()
        self.assertEqual(len(zitate), 52)
        self.assertEqual(len({(entry["text"], entry["autor"]) for entry in zitate}), 52)

    def test_every_quote_has_an_existing_portrait(self):
        for entry in MODULE.load_zitate():
            image = PROJECT_DIR / "resources" / "zitate" / entry["bild"]
            self.assertTrue(image.is_file(), image)

    def test_selection_is_stable_and_changes_daily(self):
        zitate = MODULE.load_zitate()
        day = date(2026, 8, 15)
        self.assertEqual(MODULE.pick_zitat(zitate, day), MODULE.pick_zitat(zitate, day))
        self.assertNotEqual(
            MODULE.pick_zitat(zitate, day),
            MODULE.pick_zitat(zitate, day + timedelta(days=1)),
        )

    def test_render_separates_quote_from_author_metadata(self):
        zitate = MODULE.load_zitate()
        for index, entry in enumerate(zitate):
            day = date.fromordinal(len(zitate) * 1000 + index)
            selected = MODULE.pick_zitat(zitate, day)
            html = MODULE.render_page(datetime.combine(day, datetime.min.time()))
            self.assertIn(f'class="zitat-author-name">{selected["autor"]}', html)
            escaped_quote = html_lib.escape(selected["text"], quote=True).replace("&#x27;", "&#39;")
            self.assertIn(f"„{escaped_quote}“", html)


if __name__ == "__main__":
    unittest.main()
