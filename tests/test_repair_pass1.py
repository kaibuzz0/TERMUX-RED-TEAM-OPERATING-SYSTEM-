"""Targeted regression tests for Hive OS Native Termux Repair Pass 1.

Covers:
- policy routing
- cwd-independent modern dispatch
- modern Hive --help
- install-termux-easy.sh dependency installation
- operations_center.cli invocation without runpy warning
- legacy fallback still works
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = REPO_ROOT / "bin" / "hive"
INSTALLER = REPO_ROOT / "install-termux-easy.sh"


class RepairPass1Tests(unittest.TestCase):
    """Regression tests for the five confirmed integration defects."""

    def _run_launcher(self, *args, cwd=None, env=None):
        env = env or os.environ.copy()
        env["HIVE_REPO_ROOT"] = str(REPO_ROOT)
        env["PYTHONPATH"] = str(REPO_ROOT)
        cmd = [sys.executable, str(LAUNCHER)] + list(args)
        result = subprocess.run(
            cmd,
            cwd=cwd or str(REPO_ROOT),
            capture_output=True,
            text=True,
            env=env,
        )
        return result

    # ── A. Installer dependency installation ──
    def test_installer_sh_uses_runtime_requirements(self):
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("requirements-runtime.txt", text,
                        "install-termux-easy.sh must install runtime requirements")
        self.assertNotIn("requirements.txt", text,
                         "install-termux-easy.sh must NOT reference full requirements.txt")

    def test_installer_sh_uses_master_not_old_tag(self):
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("master", text,
                        "install-termux-easy.sh must clone master branch")
        self.assertNotIn("hive-os-v1.0.0", text,
                         "install-termux-easy.sh must NOT reference old v1.0.0 tag")

    def test_installer_sh_error_on_failure(self):
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("exit 1", text,
                      "install-termux-easy.sh must stop on pip failure")

    # ── B. CWD-independent modern dispatch ──
    def test_config_validate_from_home(self):
        result = self._run_launcher("config", "validate", cwd=str(Path.home()))
        self.assertEqual(result.returncode, 0,
                         f"config validate from $HOME must succeed: {result.stderr}")

    def test_policy_status_from_home(self):
        result = self._run_launcher("policy", "status", cwd=str(Path.home()))
        self.assertEqual(result.returncode, 0,
                         f"policy status from $HOME must succeed: {result.stderr}")

    def test_broker_capabilities_from_home(self):
        result = self._run_launcher("broker", "capabilities", cwd=str(Path.home()))
        self.assertEqual(result.returncode, 0,
                         f"broker capabilities from $HOME must succeed: {result.stderr}")

    def test_config_validate_from_unrelated_dir(self):
        with tempfile.TemporaryDirectory() as other:
            result = self._run_launcher("config", "validate", cwd=other)
            self.assertEqual(result.returncode, 0,
                             f"config validate from unrelated dir must succeed: {result.stderr}")

    def test_policy_status_from_unrelated_dir(self):
        with tempfile.TemporaryDirectory() as other:
            result = self._run_launcher("policy", "status", cwd=other)
            self.assertEqual(result.returncode, 0,
                             f"policy status from unrelated dir must succeed: {result.stderr}")

    # ── C. Policy routing ──
    def test_policy_route_exists(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('if argv[1:] and argv[1] == "policy":', text,
                      "launcher must have policy route")
        self.assertIn("policy_engine.cli", text,
                      "policy route must delegate to policy_engine.cli")

    # ── D. Modern help ──
    def test_help_shows_modern_commands(self):
        result = self._run_launcher("--help")
        self.assertEqual(result.returncode, 0)
        out = result.stdout
        self.assertIn("Modern Hive OS commands", out,
                        "help must document modern commands")
        self.assertIn("config", out, "help must list config")
        self.assertIn("policy", out, "help must list policy")
        self.assertIn("broker", out, "help must list broker")
        self.assertIn("ops", out, "help must list ops")

    def test_help_shows_legacy_compatibility(self):
        result = self._run_launcher("--help")
        self.assertIn("Legacy compatibility commands", result.stdout,
                      "help must document legacy commands")

    def test_help_does_not_look_like_legacy_only(self):
        result = self._run_launcher("--help")
        # Legacy-only help starts with "Hive Ops Final"
        self.assertNotIn("Hive Ops Final - Unified Command Interface", result.stdout,
                         "hive --help must NOT look like legacy-only help")

    # ── E. Operations Center runpy warning ──
    def test_operations_center_cli_no_runpy_warning(self):
        cmd = [sys.executable, "-m", "operations_center.cli"]
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertNotIn("RuntimeWarning", result.stderr,
                         "operations_center.cli must not produce runpy warning")

    def test_operations_center_package_has_lazy_main(self):
        init = REPO_ROOT / "operations_center" / "__init__.py"
        text = init.read_text(encoding="utf-8")
        self.assertIn("def main", text,
                      "operations_center.__init__ must define main lazily")
        self.assertIn("from operations_center.cli import", text,
                      "lazy import must happen inside main, not at top level")

    # ── Legacy fallback still works ──
    def test_legacy_resolve_still_works(self):
        result = self._run_launcher("--resolve")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Hive Ops Final", result.stdout,
                        "legacy --resolve must still function")


if __name__ == "__main__":
    unittest.main()
