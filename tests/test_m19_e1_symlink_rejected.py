"""E1-SYMLINK: Symlink trust store files are rejected.

An attacker replacing the trust store PEM with a symlink could redirect
to an attacker-controlled key file. The canonical defense is to reject
symlinks at load time and return an empty store (fail-closed).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from updates.trust import TrustStore, TrustError
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

class TestSymlinkTrustStoreRejected:
    """Symlink trust store files must be rejected."""

    def test_symlink_trust_store_rejected(self):
        """TrustStore.from_pem_file rejects symlinks (fail-closed)."""
        priv = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            real_pem = Path(tmp) / "real.pem"
            real_pem.write_text(export_public_key_pem(priv.public_key(), "real-key"))
            link = Path(tmp) / "link.pem"
            link.symlink_to(real_pem)
            # Symlink must be rejected
            ts = TrustStore.from_pem_file(link)
            assert ts.keys == {}, "Symlink trust store must fail closed (empty store)"
            with pytest.raises(TrustError, match="Unknown key ID"):
                ts.verify("real-key", b"msg", b"sig")

    def test_symlink_to_directory_rejected(self):
        """TrustStore.from_pem_file rejects symlinks to directories."""
        with tempfile.TemporaryDirectory() as tmp:
            real_dir = Path(tmp) / "real_dir"
            real_dir.mkdir()
            link = Path(tmp) / "link_dir.pem"
            link.symlink_to(real_dir)
            ts = TrustStore.from_pem_file(link)
            assert ts.keys == {}

    def test_regular_file_still_loads(self):
        """Regular (non-symlink) PEM files continue to load normally."""
        priv = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            real_pem = Path(tmp) / "real.pem"
            real_pem.write_text(export_public_key_pem(priv.public_key(), "real-key"))
            ts = TrustStore.from_pem_file(real_pem)
            assert "real-key" in ts.keys

    def test_hardlink_trust_store_accepted(self):
        """Hardlinks are accepted (same inode, indistinguishable from regular file)."""
        priv = Ed25519PrivateKey.generate()
        with tempfile.TemporaryDirectory() as tmp:
            real_pem = Path(tmp) / "real.pem"
            real_pem.write_text(export_public_key_pem(priv.public_key(), "real-key"))
            hard = Path(tmp) / "hard.pem"
            import os
            os.link(real_pem, hard)
            ts = TrustStore.from_pem_file(hard)
            assert "real-key" in ts.keys