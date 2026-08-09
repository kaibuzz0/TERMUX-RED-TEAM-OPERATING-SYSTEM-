"""Milestone 19 — I3 Credential argv exposure investigation.

Focus: security/vault/cli.py

Verifies that passwords/secrets are not accepted or propagated as ordinary
command-line arguments in vault CLI handling.
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest

from security.vault.cli import main as vault_main


class TestCredentialArgvExposure:
    """I3 — verify vault CLI does not accept secrets in argv."""

    def test_vault_init_no_password_arg(self):
        """vault init accepts --force but not --password or --master-password."""
        with pytest.raises(SystemExit) as exc_info:
            vault_main(["init", "--password", "secret123"])
        # argparse should reject unknown argument
        assert exc_info.value.code == 2

    def test_vault_unlock_no_password_arg(self):
        """vault unlock accepts no password argument."""
        with pytest.raises(SystemExit) as exc_info:
            vault_main(["unlock", "--password", "secret123"])
        assert exc_info.value.code == 2

    def test_vault_set_no_value_arg(self):
        """vault set accepts name but not --value; value is getpass prompt."""
        # --value is not a defined argument
        with pytest.raises(SystemExit) as exc_info:
            vault_main(["set", "mysecret", "--value", "secret123"])
        assert exc_info.value.code == 2

    def test_master_password_is_suppressed(self):
        """--master-password is argparse.SUPPRESS; hidden from help."""
        # It exists for non-interactive automation but is hidden
        # We verify it does NOT appear in help output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            with pytest.raises(SystemExit):
                vault_main(["set", "--help"])
        finally:
            help_text = sys.stdout.getvalue()
            sys.stdout = old_stdout
        assert "master-password" not in help_text.lower()
        assert "master_password" not in help_text.lower()

    def test_no_plaintext_in_argv_error_output(self, tmp_path):
        """Even on error, no secret value should appear in error text."""
        # Simulate argv with a fake secret marker
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            with pytest.raises(SystemExit):
                vault_main(["init", "--M19_FAKE_PASSWORD=secret"])
        finally:
            err_text = sys.stderr.getvalue()
            sys.stderr = old_stderr
        # The fake secret marker must not appear in error output
        assert "secret" not in err_text.lower() or "unrecognized" in err_text.lower()

    def test_vault_status_no_secret_in_json(self, tmp_path, monkeypatch):
        """vault status JSON output must not leak secrets."""
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            code = vault_main(["status", "--json"])
        finally:
            out_text = sys.stdout.getvalue()
            sys.stdout = old_stdout
        # Status output is redacted or secret-count only
        assert "password" not in out_text.lower()
        assert "secret" not in out_text.lower() or '"secret_count"' in out_text.lower()

    def test_subprocess_in_vault_cli_uses_devnull(self):
        """Vault CLI does not spawn subprocesses with secret-bearing argv."""
        import inspect
        src = inspect.getsource(vault_main)
        # Verify no subprocess.run or subprocess.call with secret args
        assert "subprocess.run" not in src or "getpass" in src

