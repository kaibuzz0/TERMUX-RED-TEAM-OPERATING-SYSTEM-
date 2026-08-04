"""Tests for Hive OS environment script and services configuration."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class EnvShTests(unittest.TestCase):
    def test_env_sh_no_root_paths(self):
        env_path = REPO_ROOT / "Hive Ops Final" / "etc" / "env.sh"
        text = env_path.read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("/root/hive", text, "env.sh must not hardcode /root/hive")
        self.assertNotIn("/root/hive-os", text, "env.sh must not hardcode /root/hive-os")
        self.assertNotIn("/root/hive-swarm", text, "env.sh must not hardcode /root/hive-swarm")

    def test_env_sh_preserves_explicit_values(self):
        env_path = REPO_ROOT / "Hive Ops Final" / "etc" / "env.sh"
        text = env_path.read_text(encoding="utf-8", errors="replace")
        # Explicit operator overrides should not be overwritten.
        self.assertIn('${HIVE_HOME:-$HOME/hive}', text)
        self.assertIn('${HIVE_OS:-$HOME/hive-os}', text)
        self.assertIn('${HIVE_SWARM:-$HOME/hive-swarm}', text)

    def test_env_sh_no_secrets_exported(self):
        env_path = REPO_ROOT / "Hive Ops Final" / "etc" / "env.sh"
        text = env_path.read_text(encoding="utf-8", errors="replace")
        for forbidden in ["PASSWORD", "TOKEN", "SECRET", "API_KEY"]:
            self.assertNotIn(forbidden, text, f"env.sh must not export secrets: {forbidden}")

    def test_env_sh_quoting(self):
        env_path = REPO_ROOT / "Hive Ops Final" / "etc" / "env.sh"
        text = env_path.read_text(encoding="utf-8", errors="replace")
        # Basic check that expansions are quoted where used in PATH.
        self.assertIn('"$HIVE_FINAL/bin:$HIVE_BIN:$HIVE_OS/bin"', text)


class ServicesJsonTests(unittest.TestCase):
    def test_services_json_valid(self):
        services_path = REPO_ROOT / "Hive Ops Final" / "etc" / "services.json"
        with open(services_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("services", data)

    def test_services_json_no_root_paths(self):
        services_path = REPO_ROOT / "Hive Ops Final" / "etc" / "services.json"
        text = services_path.read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("/root/hive", text, "services.json must not hardcode /root/hive")
        self.assertNotIn("/root/Hive Ops Final", text, "services.json must not hardcode /root/Hive Ops Final")

    def test_services_json_no_new_services(self):
        services_path = REPO_ROOT / "Hive Ops Final" / "etc" / "services.json"
        with open(services_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(set(data["services"].keys()), {"hive-daemon", "swarm-registry", "watchdog"})

    def test_services_json_no_listener_changes(self):
        services_path = REPO_ROOT / "Hive Ops Final" / "etc" / "services.json"
        with open(services_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # No bind addresses should be introduced.
        for svc in data["services"].values():
            for field in ["start", "stop", "status", "restart"]:
                if field in svc:
                    self.assertNotIn("0.0.0.0", svc[field])


if __name__ == "__main__":
    unittest.main()
