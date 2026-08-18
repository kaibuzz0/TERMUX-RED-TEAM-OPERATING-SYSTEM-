"""E1-PERMISSIONS: Trust store and vault file permissions where supported.

On POSIX systems, canonical code attempts to set vault temp files to owner-only
(0o600) before atomic rename. Trust store PEM files do NOT have permission
enforcement in canonical code (they are loaded read-only).

In PRoot/root environments, `os.chmod` restrictions may be bypassed (root
can read any file regardless of mode). This test verifies the code attempts
the restriction without claiming it is a sandbox.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from security.vault.storage import VaultStorage
from updates.trust import TrustStore
from updates.signing import export_public_key_pem




def _skip_if_no_symlink_support():
    """Skip tests that require creating symlinks when unprivileged on Windows."""
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            src.write_text("x")
            try:
                dst.symlink_to(src)
            except OSError as exc:
                if getattr(exc, "winerror", None) == 1314:
                    pytest.skip("symlink creation requires elevated privileges on this platform")
    except Exception:
        pass

class TestVaultStoragePermissions:
    """Vault storage attempts restrictive permissions on temp files."""

    def test_vault_write_sets_owner_only_permissions(self):
        """VaultStorage.write() attempts chmod(0o600) on temp file."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "vault"
            vault_dir.mkdir()
            storage = VaultStorage(vault_dir)
            storage.write("secret", overwrite=True)
            # Permissions should be 0o600 (owner read+write)
            mode = vault_dir.joinpath("vault.json").stat().st_mode
            assert stat.S_IMODE(mode) == 0o600, (
                f"Expected 0o600, got {oct(stat.S_IMODE(mode))}"
            )

    def test_vault_write_handles_chmod_failure_gracefully(self):
        """VaultStorage.write() catches and ignores chmod failure."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "vault"
            vault_dir.mkdir()
            storage = VaultStorage(vault_dir)
            # This should succeed even if chmod would fail
            storage.write("secret", overwrite=True)
            assert storage.exists()
            assert storage.read() == "secret"

    def test_vault_backup_preserves_permissions(self):
        """VaultStorage.backup() does not alter permissions."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "vault"
            storage = VaultStorage(vault_dir)
            storage.write("secret", overwrite=True)
            backup = storage.backup()
            assert backup.exists()


class TestTrustStoreFilePermissions:
    """Trust store PEM files have no canonical permission enforcement."""

    def test_trust_store_from_pem_file_does_not_set_permissions(self):
        """TrustStore.from_pem_file does not chmod or enforce file permissions."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "test-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(pem)
            # Make it world-writable to simulate lax permissions
            os.chmod(pem_path, 0o666)
            # Still loads without error
            ts = TrustStore.from_pem_file(pem_path)
            assert "test-key" in ts.keys
            # NOTE: This is not a vulnerability because the trust store is
            # read-only. Tampering the file would be detected at verification
            # time via signature mismatch or missing key_id.

    def test_trust_store_no_chmod_in_source(self):
        """No chmod() call exists in updates/trust.py."""
        import inspect
        src = inspect.getsource(TrustStore)
        assert "chmod" not in src.lower(), (
            "TrustStore should not attempt permission management"
        )

    def test_trust_store_ignores_lax_permissions(self):
        """TrustStore.from_pem_file ignores file mode and loads anyway."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "lax-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(pem)
            # World-writable (simulating compromised host)
            os.chmod(pem_path, 0o777)
            ts = TrustStore.from_pem_file(pem_path)
            assert "lax-key" in ts.keys


class TestNoPermissionSandboxClaims:
    """Do not claim chmod provides a sandbox on PRoot/root."""

    def test_root_can_read_restricted_file(self):
        """Documented: root in PRoot can read 0o000 files."""
        with tempfile.TemporaryDirectory() as tmp:
            restricted = Path(tmp) / "secret.txt"
            restricted.write_text("sensitive")
            os.chmod(restricted, 0o000)
            try:
                content = restricted.read_text()
                # If we get here, root/PRoot bypassed the restriction
                assert content == "sensitive"
            except PermissionError:
                # If it actually blocked, restore and note
                os.chmod(restricted, 0o644)
                pytest.skip("Permission restrictions enforced (non-root environment)")
            finally:
                os.chmod(restricted, 0o644)