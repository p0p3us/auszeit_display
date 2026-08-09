import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import display_state


class DisplayStateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.state_file = self.data_dir / "display_state.json"

        self.data_dir_patch = patch.object(display_state, "DATA_DIR", self.data_dir)
        self.state_file_patch = patch.object(display_state, "STATE_FILE", self.state_file)
        self.data_dir_patch.start()
        self.state_file_patch.start()

    def tearDown(self):
        self.state_file_patch.stop()
        self.data_dir_patch.stop()
        self.temp_dir.cleanup()

    def read_saved_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def test_missing_file_creates_default_state(self):
        state = display_state.get_display_state()

        self.assertEqual(state, display_state.DEFAULT_STATE)
        self.assertEqual(self.read_saved_state(), display_state.DEFAULT_STATE)

    def test_invalid_json_is_replaced_with_default_state(self):
        self.state_file.write_text("{invalid", encoding="utf-8")

        state = display_state.get_display_state()

        self.assertEqual(state, display_state.DEFAULT_STATE)
        self.assertEqual(self.read_saved_state(), display_state.DEFAULT_STATE)

    def test_non_object_json_is_replaced_with_default_state(self):
        self.state_file.write_text("[]", encoding="utf-8")

        state = display_state.get_display_state()

        self.assertEqual(state, display_state.DEFAULT_STATE)
        self.assertEqual(self.read_saved_state(), display_state.DEFAULT_STATE)

    def test_invalid_active_page_is_replaced_with_default(self):
        self.state_file.write_text('{"active_page": 123}', encoding="utf-8")

        state = display_state.get_display_state()

        self.assertEqual(state, display_state.DEFAULT_STATE)
        self.assertEqual(self.read_saved_state(), display_state.DEFAULT_STATE)

    def test_valid_state_is_preserved(self):
        expected = {"active_page": "news/current.html", "extra": True}
        self.state_file.write_text(json.dumps(expected), encoding="utf-8")

        self.assertEqual(display_state.get_display_state(), expected)


if __name__ == "__main__":
    unittest.main()
