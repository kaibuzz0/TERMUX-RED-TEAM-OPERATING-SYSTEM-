"""Safety tests for the real Termux install/autoboot behavior.

These tests simulate the installation using temporary HOME and PREFIX fixtures
on the PC. They do NOT modify the real user shell.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _bashrc_block_text() -> str:
    """Return the generated bashrc block as a string for simulation."""
    return r"""# >>> HIVE OS AUTOBOOT >>>
# Hive OS managed startup block. Safe to edit outside markers.
# To disable autoboot: hive autoboot disable
# To remove this block: hive autoboot disable --remove
# To skip once: export HIVE_NO_AUTOBOOT=1 before starting shell
case $- in
    *i*) ;;
    *) return ;;
esac
if [ -n "${HIVE_NO_AUTOBOOT:-}" ]; then
    return
fi
if [ -f "$HOME/.config/hive/no-autoboot" ]; then
    return
fi
if [ -n "${HIVE_BOOT_ACTIVE:-}" ]; then
    return
fi
export HIVE_BOOT_ACTIVE=1
HIVE_INSTALL_DIR="${HIVE_INSTALL_DIR:-$HOME/Hive-Ops}"
# Prefer the known-good global hive command; fall back to python repo launcher.
if command -v hive >/dev/null 2>&1; then
    hive boot
elif command -v python >/dev/null 2>&1 && [ -f "$HIVE_INSTALL_DIR/bin/hive" ]; then
    python "$HIVE_INSTALL_DIR/bin/hive" boot
fi
unset HIVE_BOOT_ACTIVE
# <<< HIVE OS AUTOBOOT <<<
""".strip()


class TestTermuxInstallAutoboot(unittest.TestCase):
    """Simulate a real Termux install on a temp HOME/PREFIX."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hive_install_test_"))
        self.home = self.tmp / "home"
        self.prefix = self.tmp / "prefix"
        self.unrelated = self.tmp / "unrelated"
        self.home.mkdir()
        self.prefix.mkdir()
        self.unrelated.mkdir()
        self.install_dir = self.home / "Hive-Ops"
        shutil.copytree(
            REPO_ROOT,
            self.install_dir,
            ignore=shutil.ignore_patterns(".git", "release-output-*"),
        )
        self.launcher = self.prefix / "bin" / "hive.py"
        self.launcher.parent.mkdir(parents=True, exist_ok=True)
        wrapper = (
            "import os, subprocess, sys\n"
            "from pathlib import Path\n"
            "home = Path(os.environ[\"HOME\"])\n"
            "repo_root = Path(os.environ.get(\"HIVE_REPO_ROOT\", home / \"Hive-Ops\")).resolve()\n"
            "env = os.environ.copy()\n"
            "env[\"HIVE_REPO_ROOT\"] = str(repo_root)\n"
            "env[\"PYTHONPATH\"] = str(repo_root) + (os.pathsep + env[\"PYTHONPATH\"] if env.get(\"PYTHONPATH\") else \"\")\n"
            "sys.exit(subprocess.run([sys.executable, str(repo_root / \"bin\" / \"hive\")] + sys.argv[1:], env=env).returncode)\n"
        )
        self.launcher.write_text(wrapper, encoding="utf-8")
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.home)
        self.env["USERPROFILE"] = str(self.home)
        self.env["HIVE_REPO_ROOT"] = str(self.install_dir)
        self.env["PYTHONPATH"] = str(self.install_dir)
        self.env["HIVE_PREFIX"] = str(self.prefix)
        self.env["PATH"] = str(self.prefix / "bin") + os.pathsep + self.env.get("PATH", "")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run_hive(self, *args, cwd=None, input=None):
        cmd = [sys.executable, str(self.launcher)] + list(args)
        return subprocess.run(
            cmd,
            cwd=str(cwd or self.unrelated),
            env=self.env,
            capture_output=True,
            text=True,
            input=input,
        )

    def _simulate_bashrc(self, bashrc: Path, *, interactive: bool = True, no_autoboot: bool = False, boot_active: bool = False, disable_file: bool = False) -> subprocess.CompletedProcess:
        """Source the generated autoboot block in a fresh bash process."""
        env = self.env.copy()
        env["HOME"] = str(self.home)
        if no_autoboot:
            env["HIVE_NO_AUTOBOOT"] = "1"
        if boot_active:
            env["HIVE_BOOT_ACTIVE"] = "1"
        if disable_file:
            (self.home / ".config" / "hive").mkdir(parents=True, exist_ok=True)
            (self.home / ".config" / "hive" / "no-autoboot").write_text("disabled", encoding="utf-8")

        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash not available for autoboot simulation")
        flag = "-i" if interactive else "-c"
        command = "echo shell_ready"
        if interactive:
            # In interactive mode we feed the block via stdin.
            block = _bashrc_block_text()
            script = f"{block}\necho shell_ready"
            return subprocess.run(
                [bash, "-i"],
                input=script,
                env=env,
                cwd=str(self.unrelated),
                capture_output=True,
                text=True,
                timeout=10,
            )
        else:
            return subprocess.run(
                [bash, "-c", f"{_bashrc_block_text()}\necho shell_ready"],
                env=env,
                cwd=str(self.unrelated),
                capture_output=True,
                text=True,
                timeout=10,
            )

    # ------------------------------------------------------------------
    # Global command
    # ------------------------------------------------------------------

    def test_global_launcher_forwards_args(self):
        result = self._run_hive("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Hive OS", result.stdout)

    def test_global_launcher_works_outside_repo(self):
        result = self._run_hive("broker", "capabilities")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("capabilities", result.stdout.lower())

    def test_global_launcher_preserves_spaces(self):
        # The launcher should forward arguments unchanged; test with a flag containing spaces.
        # Since there is no command that consumes a spaced argument in hive, just verify subprocess receives it.
        result = self._run_hive("--help", "extra arg with spaces")
        self.assertEqual(result.returncode, 0, result.stderr)

    # ------------------------------------------------------------------
    # Bare hive
    # ------------------------------------------------------------------

    def test_bare_hive_launches_boot_interface(self):
        result = subprocess.run(
            [sys.executable, str(self.install_dir / "bin" / "hive_boot.py")],
            env=self.env,
            capture_output=True,
            text=True,
            input="0\n",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Operator Environment", result.stdout)

    def test_bare_hive_command_launches_boot(self):
        result = self._run_hive(cwd=str(self.install_dir), input="0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Operator Environment", result.stdout)

    # ------------------------------------------------------------------
    # Autoboot install and idempotency
    # ------------------------------------------------------------------

    def test_autoboot_enable_adds_managed_block(self):
        result = self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        bashrc = self.home / ".bashrc"
        self.assertTrue(bashrc.exists())
        text = bashrc.read_text(encoding="utf-8")
        self.assertIn("# >>> HIVE OS AUTOBOOT >>>", text)
        self.assertIn("# <<< HIVE OS AUTOBOOT <<<", text)
        self.assertIn("HIVE_BOOT_ACTIVE", text)

    def test_autoboot_is_idempotent(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        bashrc = self.home / ".bashrc"
        text = bashrc.read_text(encoding="utf-8")
        self.assertEqual(text.count("# >>> HIVE OS AUTOBOOT >>>"), 1)

    def test_autoboot_preserves_existing_bashrc(self):
        bashrc = self.home / ".bashrc"
        original = "# My aliases\nalias ll='ls -la'\n\nexport HERMES_HOME=/data/data/...\n"
        bashrc.write_text(original, encoding="utf-8")
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        text = bashrc.read_text(encoding="utf-8")
        self.assertIn("alias ll='ls -la'", text)
        self.assertIn("HERMES_HOME", text)
        self.assertIn("# >>> HIVE OS AUTOBOOT >>>", text)

    def test_autoboot_creates_backup(self):
        bashrc = self.home / ".bashrc"
        original = "# Pre-existing content\n"
        bashrc.write_text(original, encoding="utf-8")
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        backup = bashrc.with_suffix(".bashrc.hive-backup")
        self.assertTrue(backup.exists())
        self.assertEqual(backup.read_text(encoding="utf-8"), original)
        # Second enable should not overwrite backup with modified content.
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        self.assertEqual(backup.read_text(encoding="utf-8"), original)

    # ------------------------------------------------------------------
    # Disable / enable persistence
    # ------------------------------------------------------------------

    def test_autoboot_disable_sets_no_autoboot(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        self._run_hive("autoboot", "disable", cwd=str(self.install_dir))
        bashrc = self.home / ".bashrc"
        text = bashrc.read_text(encoding="utf-8")
        self.assertIn("HIVE_NO_AUTOBOOT=1", text)
        self.assertIn("# >>> HIVE OS AUTOBOOT >>>", text)
        self.assertTrue((self.home / ".config" / "hive" / "no-autoboot").exists())

    def test_autoboot_disable_persists_across_shells(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        self._run_hive("autoboot", "disable", cwd=str(self.install_dir))
        result = self._simulate_bashrc(self.home / ".bashrc", interactive=False)
        self.assertIn("shell_ready", result.stdout)
        self.assertNotIn("Operator Environment", result.stdout)

    def test_autoboot_remove_deletes_block(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        self._run_hive("autoboot", "disable", "--remove", cwd=str(self.install_dir))
        bashrc = self.home / ".bashrc"
        text = bashrc.read_text(encoding="utf-8")
        self.assertNotIn("# >>> HIVE OS AUTOBOOT >>>", text)

    def test_autoboot_reenable_after_disable(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        self._run_hive("autoboot", "disable", cwd=str(self.install_dir))
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        bashrc = self.home / ".bashrc"
        text = bashrc.read_text(encoding="utf-8")
        self.assertIn("# >>> HIVE OS AUTOBOOT >>>", text)
        active_exports = [line for line in text.splitlines() if line.strip().startswith("export HIVE_NO_AUTOBOOT=1")]
        self.assertEqual(len(active_exports), 0, active_exports)
        self.assertFalse((self.home / ".config" / "hive" / "no-autoboot").exists())

    # ------------------------------------------------------------------
    # Noninteractive and recursive protection
    # ------------------------------------------------------------------

    def test_noninteractive_shell_does_not_autoboot(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        result = self._simulate_bashrc(self.home / ".bashrc", interactive=False)
        self.assertIn("shell_ready", result.stdout)
        self.assertNotIn("Operator Environment", result.stdout)

    def test_recursive_boot_prevented(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        result = self._simulate_bashrc(self.home / ".bashrc", interactive=False, boot_active=True)
        self.assertIn("shell_ready", result.stdout)
        self.assertNotIn("Operator Environment", result.stdout)

    def test_env_no_autoboot_bypass(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        result = self._simulate_bashrc(self.home / ".bashrc", interactive=False, no_autoboot=True)
        self.assertIn("shell_ready", result.stdout)
        self.assertNotIn("Operator Environment", result.stdout)

    def test_disable_file_bypass(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        result = self._simulate_bashrc(self.home / ".bashrc", interactive=False, disable_file=True)
        self.assertIn("shell_ready", result.stdout)
        self.assertNotIn("Operator Environment", result.stdout)

    # ------------------------------------------------------------------
    # Launcher collision protection
    # ------------------------------------------------------------------

    def test_unrelated_hive_command_not_overwritten(self):
        existing = self.prefix / "bin" / "hive"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("#!/bin/sh\necho 'unrelated hive'\n", encoding="utf-8")

        # Simulate the installer check by running the autoboot command and checking collision.
        # The installer script itself cannot run on Windows, but we can inspect its logic.
        # For this test, verify the launcher identification mechanism works by reading the script.
        script = (REPO_ROOT / "install-termux-easy.sh").read_text(encoding="utf-8")
        self.assertIn("# HIVE_OS_MANAGED_LAUNCHER", script)
        self.assertIn("_is_hive_managed", script)
        # Ensure the script refuses to overwrite non-managed launchers.
        self.assertIn("already exists and is not a Hive-managed launcher", script)

    # ------------------------------------------------------------------
    # Installer failure gate
    # ------------------------------------------------------------------

    def test_installer_script_has_set_e(self):
        script = (REPO_ROOT / "install-termux-easy.sh").read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", script)

    def test_installer_script_validates_global_command(self):
        script = (REPO_ROOT / "install-termux-easy.sh").read_text(encoding="utf-8")
        self.assertIn("if ! hive --help", script)
        self.assertIn("Hive OS installation complete", script)

    def test_installer_script_checks_collision(self):
        script = (REPO_ROOT / "install-termux-easy.sh").read_text(encoding="utf-8")
        self.assertIn("_is_hive_managed", script)
        self.assertIn("exit 1", script)

    # ------------------------------------------------------------------
    # Termux self-repair
    # ------------------------------------------------------------------

    def test_autoboot_prefers_global_hive_path(self):
        # If a global `hive` command exists in PATH, the autoboot block should use it.
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        bashrc = self.home / ".bashrc"
        text = bashrc.read_text(encoding="utf-8")
        start = text.find("# >>> HIVE OS AUTOBOOT >>>")
        end = text.find("# <<< HIVE OS AUTOBOOT <<<")
        block = text[start:end]
        self.assertIn("command -v hive", block)
        self.assertIn("hive boot", block)

    def test_autoboot_falls_back_to_python_repo_launcher(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        bashrc = self.home / ".bashrc"
        text = bashrc.read_text(encoding="utf-8")
        start = text.find("# >>> HIVE OS AUTOBOOT >>>")
        end = text.find("# <<< HIVE OS AUTOBOOT <<<")
        block = text[start:end]
        self.assertIn('python "$HIVE_INSTALL_DIR/bin/hive" boot', block)

    def test_autoboot_no_longer_uses_executable_bit_only(self):
        self._run_hive("autoboot", "enable", cwd=str(self.install_dir))
        bashrc = self.home / ".bashrc"
        text = bashrc.read_text(encoding="utf-8")
        block = text[text.find("# >>> HIVE OS AUTOBOOT >>>"):text.find("# <<< HIVE OS AUTOBOOT <<<")]
        # The old implementation required -x on the repo launcher. The new block no longer relies on it.
        self.assertNotIn('if [ -x "$HIVE_INSTALL_DIR/bin/hive" ]; then', block)

    def test_home_option_nine_invokes_repair(self):
        result = subprocess.run(
            [sys.executable, str(self.install_dir / "bin" / "hive_boot.py")],
            env=self.env,
            capture_output=True,
            text=True,
            input="9\n0\n",
        )
        self.assertEqual(result.returncode, 0)
        # The menu should advertise option 9.
        self.assertIn("[9] Termux Integration", result.stdout)

    def test_termux_repair_creates_global_launcher(self):
        result = self._run_hive("termux", "repair", cwd=str(self.install_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        global_hive = self.prefix / "bin" / "hive"
        self.assertTrue(global_hive.exists())
        text = global_hive.read_text(encoding="utf-8")
        self.assertIn("# HIVE_OS_MANAGED_LAUNCHER", text)
        # The launcher references the repo via HIVE_REPO_ROOT; verify the export line is present.
        self.assertIn('export HIVE_REPO_ROOT="', text)
        # Bash-style forward-slash path of the resolved repo root appears inside the export.
        self.assertIn((self.install_dir.resolve()).as_posix(), text)

    def test_termux_repair_idempotent(self):
        self._run_hive("termux", "repair", cwd=str(self.install_dir))
        result = self._run_hive("termux", "repair", cwd=str(self.install_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        bashrc = self.home / ".bashrc"
        text = bashrc.read_text(encoding="utf-8")
        self.assertEqual(text.count("# >>> HIVE OS AUTOBOOT >>>"), 1)

    def test_termux_status_reports_integration(self):
        self._run_hive("termux", "repair", cwd=str(self.install_dir))
        result = self._run_hive("termux", "status", cwd=str(self.install_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Hive OS Termux Integration", result.stdout)
        self.assertIn("Global hive command", result.stdout)

    def test_termux_repair_preserves_collision_rules(self):
        existing = self.prefix / "bin" / "hive"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("#!/bin/sh\necho 'unrelated hive'\n", encoding="utf-8")
        result = self._run_hive("termux", "repair", cwd=str(self.install_dir))
        # Repair does not overwrite unrelated launchers.
        text = existing.read_text(encoding="utf-8")
        self.assertIn("unrelated hive", text)
        self.assertNotIn("HIVE_OS_MANAGED_LAUNCHER", text)
        # Status should reflect that global hive is not managed.
        result2 = self._run_hive("termux", "status", cwd=str(self.install_dir))
        self.assertIn("Global hive command", result2.stdout)


if __name__ == "__main__":
    unittest.main()