from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "generate_weisheit.py"
SPEC = importlib.util.spec_from_file_location("generate_weisheit", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WeisheitTests(unittest.TestCase):
    def test_source_contains_all_71_unique_weisheiten(self):
        weisheiten = MODULE.load_weisheiten()
        self.assertEqual(len(weisheiten), 71)
        self.assertEqual(len(set(weisheiten)), 71)
        self.assertIn("\n", weisheiten[0])

    def test_selection_is_stable_for_the_same_day(self):
        weisheiten = MODULE.load_weisheiten()
        day = date(2026, 8, 15)
        self.assertEqual(
            MODULE.pick_weisheit(weisheiten, day),
            MODULE.pick_weisheit(weisheiten, day),
        )

    def test_selection_changes_on_the_next_day(self):
        weisheiten = MODULE.load_weisheiten()
        day = date(2026, 8, 15)
        self.assertNotEqual(
            MODULE.pick_weisheit(weisheiten, day),
            MODULE.pick_weisheit(weisheiten, day + timedelta(days=1)),
        )


if __name__ == "__main__":
    unittest.main()
