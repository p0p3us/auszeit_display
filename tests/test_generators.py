import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class GeneratorTests(unittest.TestCase):
    def test_weekly_special_slide_uses_menu_fields_and_ignores_legacy_saturday(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            base = Path(temporary_dir)
            template_dir = base / "templates" / "display_pages"
            template_dir.mkdir(parents=True)
            for name in (
                "menue_uebersicht.html",
                "menue_tag.html",
                "menue_wochenschmankerl.html",
            ):
                shutil.copy2(PROJECT_DIR / "templates" / "display_pages" / name, template_dir / name)
            (base / "data").mkdir()
            payload = {
                "status": "ok",
                "period": {"start_date": "2099-09-22", "end_date": "2099-09-25"},
                "days": [],
                "has_weekly_special": True,
                "weekly_special": {
                    "title": "Zander vom Grill",
                    "description": "mit Petersilienerdäpfeln",
                    "price": "16,90",
                },
                "has_saturday_special": True,
                "saturday_special": {"title": "Altes Samstagsangebot", "date": "2099-09-26"},
            }
            data_file = base / "data" / "menue.json"
            environment = os.environ.copy()
            environment["AUSZEIT_DISPLAY_BASE_DIR"] = str(base)

            def export():
                data_file.write_text(json.dumps(payload), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(PROJECT_DIR / "scripts" / "export_menue.py")],
                    env=environment, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                page = base / "pages" / "menue" / "wochenschmankerl.html"
                return page.read_text(encoding="utf-8"), json.loads(
                    (base / "data" / "menue_status.json").read_text(encoding="utf-8")
                )

            html, status = export()
            self.assertIn("Zander vom Grill", html)
            self.assertIn("mit Petersilienerdäpfeln", html)
            self.assertIn("€ 16,90", html)
            self.assertNotIn("Altes Samstagsangebot", html)
            self.assertTrue(status["slides"]["weekly"]["available"])

            payload["has_weekly_special"] = False
            html, status = export()
            self.assertIn("Das Wochenschmankerl folgt", html)
            self.assertFalse(status["slides"]["weekly"]["available"])

    def test_base_template_does_not_render_hidden_timestamp_footer(self):
        template = (
            PROJECT_DIR / "templates" / "display_pages" / "base_display.html"
        ).read_text(encoding="utf-8")

        self.assertNotIn("display-footer", template)
        self.assertNotIn("footer_left", template)
        self.assertNotIn("footer_right", template)

    def test_event_template_uses_vertical_meta_rows_and_text_fitting(self):
        template = (PROJECT_DIR / "templates" / "display_pages" / "termin.html").read_text(
            encoding="utf-8"
        )
        stylesheet = (
            PROJECT_DIR / "static" / "css" / "display_pages" / "termine.css"
        ).read_text(encoding="utf-8")

        self.assertNotIn("event-image-fade", template)
        self.assertNotIn("event-image-fade", stylesheet)
        self.assertLess(template.index("Preis / Eintritt"), template.index("Reservierung"))
        self.assertIn("flex-direction: column", stylesheet)
        self.assertIn("fitText(document.querySelector('.event-copy'), 26, 68)", template)

    def test_generators_create_nonempty_html_pages(self):
        scripts = (
            "generate_namenstag.py",
            "generate_bauernregel.py",
            "generate_weisheit.py",
            "generate_zitat.py",
            "generate_news.py",
            "generate_weather.py",
            "export_menue.py",
            "generate_termine.py",
        )
        expected_pages = (
            "pages/namenstag/anzeige.html",
            "pages/bauernregel/anzeige.html",
            "pages/weisheit/anzeige.html",
            "pages/zitat/anzeige.html",
            "pages/news/index.html",
            "pages/weather/index.html",
            "pages/weather/morgen.html",
            "pages/weather/5tage.html",
            "pages/menue/uebersicht.html",
            "pages/menue/wochenschmankerl.html",
            "pages/menue/heute.html",
            "pages/menue/morgen.html",
            "pages/termine/termin-1.html",
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

            (test_project / "data" / "termine.json").write_text(
                json.dumps({
                    "status": "ok",
                    "events": [{
                        "date": "2099-08-20",
                        "time": "19:30",
                        "title": "Testabend",
                        "description": "Ein Testtermin",
                        "price": "Freier Eintritt",
                        "reservation": "Reservierung erbeten",
                        "image_path": "",
                    }],
                }),
                encoding="utf-8",
            )

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
