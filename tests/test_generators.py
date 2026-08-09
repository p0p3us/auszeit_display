import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class GeneratorTests(unittest.TestCase):
    def test_generators_create_nonempty_html_pages(self):
        scripts = (
            "generate_namenstag.py",
            "generate_bauernregel.py",
            "generate_news.py",
            "generate_weather.py",
            "export_menue.py",
        )
        expected_pages = (
            "pages/namenstag/anzeige.html",
            "pages/bauernregel/anzeige.html",
            "pages/news/index.html",
            "pages/weather/index.html",
            "pages/weather/morgen.html",
            "pages/weather/5tage.html",
            "pages/menue/uebersicht.html",
            "pages/menue/samstag.html",
            "pages/menue/heute.html",
            "pages/menue/morgen.html",
        )

        with tempfile.TemporaryDirectory() as temporary_dir:
            test_project = Path(temporary_dir) / "auszeit_display"
            shutil.copytree(
                PROJECT_DIR,
                test_project,
                ignore=shutil.ignore_patterns(".git", "venv", ".venv", "__pycache__"),
            )

            environment = os.environ.copy()
            environment["AUSZEIT_DISPLAY_BASE_DIR"] = str(test_project)

            for script in scripts:
                with self.subTest(script=script):
                    result = subprocess.run(
                        [sys.executable, str(test_project / "scripts" / script)],
                        env=environment,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        f"{script}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
                    )

            for relative_path in expected_pages:
                with self.subTest(page=relative_path):
                    output_file = test_project / relative_path
                    self.assertTrue(output_file.is_file(), f"Fehlt: {relative_path}")
                    self.assertGreater(output_file.stat().st_size, 0, f"Leer: {relative_path}")


if __name__ == "__main__":
    unittest.main()
