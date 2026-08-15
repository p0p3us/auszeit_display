import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "scripts"
SHELL_SCRIPTS = sorted(SCRIPTS_DIR.glob("*.sh"))


class ShellScriptTests(unittest.TestCase):
    def test_all_shell_scripts_have_valid_bash_syntax(self):
        result = subprocess.run(
            ["bash", "-n", *map(str, SHELL_SCRIPTS)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shell_scripts_do_not_contain_fixed_install_path(self):
        for script in SHELL_SCRIPTS:
            with self.subTest(script=script.name):
                self.assertNotIn("/home/pi/auszeit_display", script.read_text())

    def test_namenstag_ftp_rejects_webroot_as_delete_target(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            base_dir = Path(temporary_dir)
            config_dir = base_dir / "config"
            config_dir.mkdir()
            (config_dir / "publish.env").write_text(
                "FTP_HOST=example.invalid\n"
                "FTP_USER=test\n"
                "FTP_PASS=test\n"
                "FTP_REMOTE_DIR=/\n"
            )

            environment = os.environ.copy()
            environment["AUSZEIT_DISPLAY_BASE_DIR"] = str(base_dir)
            result = subprocess.run(
                ["bash", str(SCRIPTS_DIR / "publish_namenstag_ftp.sh")],
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unsicheres FTP-Ziel", result.stderr)

    def test_namenstag_publishers_limit_delete_to_namenstag(self):
        ftp_script = (SCRIPTS_DIR / "publish_namenstag_ftp.sh").read_text()
        rsync_script = (SCRIPTS_DIR / "publish_namenstag_rsync.sh").read_text()

        self.assertIn(
            'mirror -R --delete "$EXPORT_DIR/namenstag" "$NAMENSTAG_REMOTE_DIR"',
            ftp_script,
        )
        self.assertIn('"$EXPORT_DIR/namenstag/"', rsync_script)
        self.assertIn('"$RSYNC_REMOTE_USER@$RSYNC_REMOTE_HOST:$NAMENSTAG_REMOTE_PATH/"', rsync_script)

    def test_webinterface_publisher_uses_positive_file_list_without_delete(self):
        script = (SCRIPTS_DIR / "publish_webinterface_ftp.sh").read_text()

        self.assertNotIn("mirror ", script)
        self.assertNotIn("--delete", script)
        self.assertIn('put "$WEB_DIR/menu_admin.php"', script)
        self.assertIn('put "$WEB_DIR/termine-admin.php"', script)
        self.assertIn('put "$WEB_DIR/includes/bootstrap.php"', script)
        self.assertIn('put "$WEB_DIR/includes/storage.php"', script)
        self.assertNotIn("data/menus", script)
        self.assertNotIn("data/termine", script)
        self.assertNotIn("uploads/events", script)
        self.assertNotIn("config/local.php\" -o", script)

    def test_webinterface_publisher_accepts_only_expected_remote_directory(self):
        script = (SCRIPTS_DIR / "publish_webinterface_ftp.sh").read_text()

        self.assertIn('/menu_admin|/menu_admin/', script)
        self.assertIn("Erlaubt ist ausschließlich /menu_admin.", script)

    def test_webinterface_uses_csrf_and_atomic_json_writes(self):
        auth = (PROJECT_DIR / "webinterface/includes/auth.php").read_text()
        storage = (PROJECT_DIR / "webinterface/includes/storage.php").read_text()
        menu_admin = (PROJECT_DIR / "webinterface/menu_admin.php").read_text()
        termine_admin = (PROJECT_DIR / "webinterface/termine-admin.php").read_text()

        self.assertIn("hash_equals", auth)
        self.assertIn("random_bytes(32)", auth)
        for page in (menu_admin, termine_admin):
            self.assertIn("auszeit_verify_csrf();", page)
            self.assertIn("auszeit_csrf_input()", page)
            self.assertNotIn("?logout=1", page)

        self.assertIn("tempnam($directory", storage)
        self.assertIn("rename($temporaryFile, $file)", storage)
        self.assertEqual(menu_admin.count("file_put_contents("), 0)
        self.assertEqual(termine_admin.count("file_put_contents("), 0)

    def test_webinterface_limits_failed_logins(self):
        auth = (PROJECT_DIR / "webinterface/includes/auth.php").read_text()
        menu = (PROJECT_DIR / "webinterface/menu_admin.php").read_text()
        events = (PROJECT_DIR / "webinterface/termine-admin.php").read_text()
        ignore = (PROJECT_DIR / ".gitignore").read_text()

        self.assertIn("AUSZEIT_DEFAULT_MAX_LOGIN_ATTEMPTS = 10", auth)
        self.assertIn("AUSZEIT_DEFAULT_LOGIN_LOCK_SECONDS = 900", auth)
        self.assertIn("REMOTE_ADDR", auth)
        self.assertIn("flock($handle, LOCK_EX)", auth)
        self.assertIn("auszeit_record_failed_login", auth)
        self.assertIn("auszeit_clear_failed_logins", auth)
        self.assertIn("loginStatus['locked']", menu)
        self.assertIn("loginStatus['locked']", events)
        self.assertIn("webinterface/data/auth/*", ignore)

    def test_webinterface_hardens_sessions_before_start(self):
        bootstrap = (PROJECT_DIR / "webinterface/includes/bootstrap.php").read_text()
        menu = (PROJECT_DIR / "webinterface/menu_admin.php").read_text()
        events = (PROJECT_DIR / "webinterface/termine-admin.php").read_text()

        self.assertIn("date_default_timezone_set('Europe/Vienna')", bootstrap)
        self.assertIn("session.use_strict_mode', '1'", bootstrap)
        self.assertIn("session.cookie_httponly', '1'", bootstrap)
        self.assertIn("session.cookie_samesite', 'Strict'", bootstrap)
        self.assertIn("session.cookie_secure', '1'", bootstrap)
        self.assertLess(bootstrap.index("session.use_strict_mode"), bootstrap.index("session_start()"))
        self.assertLess(bootstrap.index("session.cookie_secure"), bootstrap.index("session_start()"))
        for page in (menu, events):
            self.assertIn("includes/bootstrap.php", page)
            self.assertNotIn("session_start();", page)

    def test_public_export_includes_event_pipeline(self):
        script = (SCRIPTS_DIR / "export_public.sh").read_text()
        self.assertIn("scripts/fetch_termine.py", script)
        self.assertIn("scripts/generate_termine.py", script)
        self.assertIn("pages/termine/", script)
        self.assertIn("resources/termine/", script)
        self.assertIn("display_pages/termine.css", script)

    def test_public_export_includes_weisheit_pipeline(self):
        script = (SCRIPTS_DIR / "export_public.sh").read_text()
        publisher = (SCRIPTS_DIR / "publish_public_ftp.sh").read_text()

        self.assertIn("scripts/generate_weisheit.py", script)
        self.assertIn("pages/weisheit/anzeige.html", script)
        self.assertIn("display_pages/weisheit.css", script)
        self.assertIn("resources/images/weisheit.png", script)
        self.assertIn("$EXPORT_DIR/weisheit/index.html", publisher)

    def test_public_export_includes_zitat_pipeline(self):
        script = (SCRIPTS_DIR / "export_public.sh").read_text()

        self.assertIn("scripts/generate_zitat.py", script)
        self.assertIn("pages/zitat/anzeige.html", script)
        self.assertIn("display_pages/zitat.css", script)
        self.assertIn("resources/zitate/", script)

    def test_public_export_preserves_unchanged_files(self):
        script = (SCRIPTS_DIR / "export_public.sh").read_text()

        self.assertIn('STAGING_DIR="$(mktemp -d', script)
        self.assertIn("trap cleanup EXIT", script)
        self.assertIn("rsync -r --delete --checksum --itemize-changes", script)
        self.assertNotIn('rm -rf "$EXPORT_DIR"', script)


if __name__ == "__main__":
    unittest.main()
