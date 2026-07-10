import contextlib
import importlib
import io
import os
import shutil
import subprocess
import sys
import sysconfig
import unittest
from unittest import mock

from game_assistant.cli import build_parser, main


PACKAGE_BOUNDARIES = (
    "game_assistant",
    "game_assistant.cli",
    "game_assistant.core",
    "game_assistant.coach",
    "game_assistant.analysis",
    "game_assistant.adapters",
    "game_assistant.storage",
    "game_assistant.vision",
    "game_assistant.replay",
    "game_assistant.recommendation",
    "game_assistant.reports",
)


def installed_console_script() -> str:
    executable = shutil.which("game-assistant")
    if executable is not None:
        return executable

    scripts_dir = sysconfig.get_path("scripts", scheme=f"{os.name}_user")
    candidates = ["game-assistant.exe", "game-assistant"]
    for candidate in candidates:
        script_path = os.path.join(scripts_dir, candidate)
        if os.path.exists(script_path):
            return script_path

    raise FileNotFoundError("game-assistant console script is not installed")


class PackageImportTests(unittest.TestCase):
    def test_package_imports(self) -> None:
        for module_name in PACKAGE_BOUNDARIES:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_imports_do_not_open_files_or_create_sockets(self) -> None:
        modules = [name for name in PACKAGE_BOUNDARIES if name in sys.modules]
        for module_name in modules:
            del sys.modules[module_name]

        with mock.patch("builtins.open", side_effect=AssertionError("unexpected file I/O")):
            with mock.patch("socket.socket", side_effect=AssertionError("unexpected socket I/O")):
                for module_name in PACKAGE_BOUNDARIES:
                    with self.subTest(module_name=module_name):
                        self.assertIsNotNone(importlib.import_module(module_name))


class CliTests(unittest.TestCase):
    def test_parser_help_identifies_project_boundary(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("local-first", help_text)
        self.assertIn("coach-only", help_text)
        self.assertIn("rhythm-game training assistant", help_text)
        self.assertIn("under active development", help_text)

    def test_main_happy_path_has_no_output(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_module_help_subprocess(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "game_assistant", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertIn("local-first", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_installed_console_script_help(self) -> None:
        result = subprocess.run(
            [installed_console_script(), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertIn("coach-only", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_unknown_argument_fails_with_actionable_error(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "game_assistant", "--unknown-option"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage:", result.stderr)
        self.assertIn("error:", result.stderr)
        self.assertIn("unrecognized arguments: --unknown-option", result.stderr)


if __name__ == "__main__":
    unittest.main()
