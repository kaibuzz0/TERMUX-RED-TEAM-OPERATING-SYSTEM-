"""Tests verifying that legacy installers exit safely by default."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _bash() -> str:
    candidates = [
        r"D:\\[]=[]=[ apps ]=[]=[]\\(((((((((((((mobile apps )))))))))))\\installed\\Git\\bin\\bash.exe",
        r"C:\\Program Files\\Git\\bin\\bash.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    bash = shutil.which("bash")
    if bash:
        return bash
    raise unittest.SkipTest("bash not available")


class LegacyBridgeDefaultExitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.tmp)
        self.env.pop("HIVE_LEGACY_UNSAFE", None)
        self.bash = _bash()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, script: str, args: list[str] | None = None) -> subprocess.CompletedProcess:
        cmd = [self.bash, str(REPO_ROOT / script)] + (args or [])
        return subprocess.run(cmd, capture_output=True, text=True, env=self.env, cwd=str(REPO_ROOT))

    def test_install_sh_default_exits_before_mutation(self):
        r = self._run("install.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("LEGACY / UNVERIFIED / NONTRANSACTIONAL", r.stdout)
        self.assertIn("python3 -m installer.install", r.stdout)
        # No directories or log files created in HOME
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_install_termux_sh_default_exits_before_mutation(self):
        r = self._run("install-termux.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("LEGACY / UNVERIFIED / NONTRANSACTIONAL", r.stdout)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_legacy_behavior_requires_env_opt_in(self):
        env = self.env.copy()
        env["HIVE_LEGACY_UNSAFE"] = "1"
        r = subprocess.run(
            [self.bash, str(REPO_ROOT / "install.sh")],
            capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
        )
        # Should proceed past guard (will fail later due to missing dependencies)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Use the new safe installer instead:", r.stdout)

    def test_legacy_behavior_requires_arg_opt_in(self):
        r = self._run("install.sh", ["--legacy-unsafe"])
        # Should proceed past guard; expected to fail later on Windows without Termux.
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Use the new safe installer instead:", r.stdout)

    def test_unrecognized_arg_does_not_enable_legacy(self):
        r = self._run("install.sh", ["--help"])
        # --help is not the unsafe opt-in; script should exit safely.
        self.assertEqual(r.returncode, 0)
        self.assertIn("LEGACY / UNVERIFIED / NONTRANSACTIONAL", r.stdout)

    def test_malformed_env_does_not_enable_legacy(self):
        env = self.env.copy()
        env["HIVE_LEGACY_UNSAFE"] = "yes"
        r = subprocess.run(
            [self.bash, str(REPO_ROOT / "install.sh")],
            capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("LEGACY / UNVERIFIED / NONTRANSACTIONAL", r.stdout)

    def test_empty_env_does_not_enable_legacy(self):
        env = self.env.copy()
        env["HIVE_LEGACY_UNSAFE"] = ""
        r = subprocess.run(
            [self.bash, str(REPO_ROOT / "install.sh")],
            capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("LEGACY / UNVERIFIED / NONTRANSACTIONAL", r.stdout)


if __name__ == "__main__":
    unittest.main()
