"""Tests for the Milestone 2 repository-level compatibility launcher.

Uses only the Python standard library. Runs on Windows for static verification;
actual Termux behavior remains unverified until physical testing.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = REPO_ROOT / "bin" / "hive"
CANONICAL_JSON = REPO_ROOT / "hive-canonical.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "compatibility-launcher"


class CompatibilityLauncherExistenceTests(unittest.TestCase):
    """Static checks for the launcher file and metadata."""

    def test_canonical_repository_launcher_exists(self):
        self.assertTrue(LAUNCHER.is_file(), "repository-level bin/hive must exist")

    def test_launcher_uses_python_shebang(self):
        with open(LAUNCHER, "r", encoding="utf-8") as f:
            shebang = f.readline()
        self.assertIn("python3", shebang.lower(), "launcher should be Python for cross-platform static testing")

    def test_launcher_contains_no_eval(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertNotIn("eval(", text, "launcher must not use eval")
        self.assertNotIn("exec(", text, "launcher should avoid exec")

    def test_launcher_contains_no_network_download(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        for forbidden in ["urllib", "requests", "httpx", "curl", "wget", "socket"]:
            self.assertNotIn(forbidden, text, f"launcher must not contain network primitive: {forbidden}")

    def test_launcher_does_not_hardcode_windows_drive(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"[A-Za-z]:\\", "launcher must not hardcode Windows paths")

    def test_launcher_does_not_hardcode_root_path(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertNotIn("/root/hive", text, "launcher must not hardcode /root/hive")

    def test_launcher_does_not_reference_devai_as_fallback(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertNotIn("Hive Ops DevAI", text, "launcher must not route to Hive Ops DevAI")
        self.assertNotIn("DevAI", text, "launcher must not route to DevAI")


class CompatibilityLauncherFunctionalTests(unittest.TestCase):
    """Functional tests that run the launcher against fixtures."""

    def _run_launcher(self, *args, cwd=None, env=None):
        env = env or os.environ.copy()
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

    def test_resolve_diagnostic(self):
        result = self._run_launcher("--resolve")
        self.assertEqual(result.returncode, 0, f"--resolve should succeed: {result.stderr}")
        self.assertIn("canonical_source", result.stdout, "resolve should show canonical source")
        self.assertIn("runtime_validation", result.stdout, "resolve should show validation status")

    def test_resolve_does_not_mutate(self):
        before = CANONICAL_JSON.stat().st_mtime
        result = self._run_launcher("--resolve")
        after = CANONICAL_JSON.stat().st_mtime
        self.assertEqual(result.returncode, 0)
        self.assertEqual(before, after, "--resolve must not mutate metadata")

    def test_resolve_from_different_directory(self):
        # Launcher should resolve repo root from its own location, not cwd.
        other_dir = str(REPO_ROOT.parent)
        result = self._run_launcher("--resolve", cwd=other_dir)
        self.assertEqual(result.returncode, 0, f"resolve from parent dir should work: {result.stderr}")
        self.assertIn("canonical_source", result.stdout)

    def test_argument_forwarding(self):
        # Forward --help; canonical launcher will either handle it or error, but our launcher
        # should pass the argument through unchanged.
        result = self._run_launcher("--help")
        # We only care that our launcher did not strip the flag.
        self.assertNotIn("hive-launcher:", result.stderr, "launcher should not fail before forwarding --help")

    def test_exit_code_forwarded_on_missing_metadata(self):
        # Create a temporary repo copy with missing metadata.
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            shutil.copytree(REPO_ROOT / "bin", tmp_root / "bin")
            shutil.copytree(REPO_ROOT / "lib", tmp_root / "lib")
            result = subprocess.run(
                [sys.executable, str(tmp_root / "bin" / "hive"), "--resolve"],
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0, "launcher should fail when metadata missing")
            self.assertTrue("missing canonical metadata" in result.stderr.lower() or "could not locate repository root" in result.stderr.lower())

    def test_rejects_malformed_metadata(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            shutil.copytree(REPO_ROOT / "bin", tmp_root / "bin")
            shutil.copytree(REPO_ROOT / "lib", tmp_root / "lib")
            (tmp_root / "hive-canonical.json").write_text("not valid json", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(tmp_root / "bin" / "hive"), "--resolve"],
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0, "launcher should fail on malformed metadata")
            self.assertIn("malformed", result.stderr.lower())

    def test_rejects_canonical_launcher_escaping_repo(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            shutil.copytree(REPO_ROOT / "bin", tmp_root / "bin")
            shutil.copytree(REPO_ROOT / "lib", tmp_root / "lib")
            (tmp_root / "Hive Ops Final").mkdir()
            (tmp_root / "Hive Ops Final" / "bin").mkdir()
            (tmp_root / "Hive Ops Final" / "bin" / "hive").write_text("# canonical", encoding="utf-8")
            metadata = {
                "schema_version": 1,
                "current_canonical_source": "Hive Ops Final",
                "current_canonical_launcher": "../outside/hive",
                "current_canonical_launcher_type": "python",
                "launcher_execution_policy": "explicit-interpreter",
                "runtime_validation": "unverified-on-termux",
            }
            (tmp_root / "hive-canonical.json").write_text(json.dumps(metadata), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(tmp_root / "bin" / "hive"), "--resolve"],
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0, "launcher should reject escape")
            self.assertIn("escapes", (result.stderr + result.stdout).lower())

    def test_rejects_canonical_launcher_outside_canonical_source(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            shutil.copytree(REPO_ROOT / "bin", tmp_root / "bin")
            shutil.copytree(REPO_ROOT / "lib", tmp_root / "lib")
            (tmp_root / "Hive Ops Final").mkdir()
            (tmp_root / "Hive Ops Final" / "bin").mkdir()
            (tmp_root / "Hive Ops Final" / "bin" / "hive").write_text("# canonical", encoding="utf-8")
            (tmp_root / "Hive Ops DevAI").mkdir()
            (tmp_root / "Hive Ops DevAI" / "bin").mkdir()
            (tmp_root / "Hive Ops DevAI" / "bin" / "hive").write_text("# devai", encoding="utf-8")
            metadata = {
                "schema_version": 1,
                "current_canonical_source": "Hive Ops Final",
                "current_canonical_launcher": "Hive Ops DevAI/bin/hive",
                "current_canonical_launcher_type": "python",
                "launcher_execution_policy": "explicit-interpreter",
                "runtime_validation": "unverified-on-termux",
            }
            (tmp_root / "hive-canonical.json").write_text(json.dumps(metadata), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(tmp_root / "bin" / "hive"), "--resolve"],
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0, "launcher should reject DevAI launcher")
            self.assertIn("not inside canonical source", (result.stderr + result.stdout).lower())

    def test_rejects_missing_canonical_source(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "repo"
            shutil.copytree(REPO_ROOT / "bin", tmp_root / "bin")
            metadata = {
                "schema_version": 1,
                "current_canonical_source": "DoesNotExist",
                "current_canonical_launcher": "bin/hive",
                "runtime_validation": "unverified-on-termux",
            }
            (tmp_root / "hive-canonical.json").write_text(json.dumps(metadata), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(tmp_root / "bin" / "hive"), "--resolve"],
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0, "launcher should fail on missing source")


class LauncherPathSafetyTests(unittest.TestCase):
    """Path-safety invariants."""

    def test_launcher_does_not_modify_bashrc(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertNotIn(".bashrc", text, "launcher must not reference .bashrc")

    def test_launcher_does_not_modify_path(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertNotIn("os.environ[\"PATH\"]", text, "launcher must not modify PATH")

    def test_launcher_does_not_install_packages(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        for forbidden in ["pip install", "pkg install", "apt-get"]:
            self.assertNotIn(forbidden, text, f"launcher must not install packages: {forbidden}")


if __name__ == "__main__":
    unittest.main()
