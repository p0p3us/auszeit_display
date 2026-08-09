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


if __name__ == "__main__":
    unittest.main()
