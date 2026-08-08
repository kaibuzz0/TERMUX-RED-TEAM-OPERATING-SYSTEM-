"""E1-NOENV: Trust store does not accept environment-injected keys.

The trust store (`updates/trust.py`) loads keys exclusively from explicit
PEM file paths or explicit PEM text strings. No environment variable is
ever consulted for key material. This test verifies the absence of
environment-based key injection.
"""

from __future__ import annotations

import inspect
import os
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from updates.trust import TrustStore, TrustError
from updates.signing import export_public_key_pem


class TestNoEnvironmentInjectedKey:
    """Trust store never reads key material from environment variables."""

    def test_trust_store_source_has_no_environ(self):
        """updates/trust.py source contains no os.environ or os.getenv."""
        import updates.trust as trust_module
        src = inspect.getsource(trust_module)
        assert "os.environ" not in src, "trust.py must not read os.environ"
        assert "os.getenv" not in src, "trust.py must not read os.getenv"
        assert "getenv" not in src, "trust.py must not use getenv"
        assert "environ" not in src, "trust.py must not reference environ"

    def test_from_pem_file_requires_explicit_path(self):
        """from_pem_file requires an explicit Path argument, not env var."""
        sig = inspect.signature(TrustStore.from_pem_file)
        params = list(sig.parameters.keys())
        assert "path" in params
        # There is no env_var parameter
        assert "env_var" not in params
        assert "environment" not in params

    def test_add_key_requires_explicit_pem_text(self):
        """add_key requires explicit PEM text, not env var lookup."""
        sig = inspect.signature(TrustStore.add_key)
        params = list(sig.parameters.keys())
        assert "key_id" in params
        assert "pem_text" in params
        assert "env_var" not in params

    def test_trust_store_not_affected_by_env_var_key_id(self):
        """Setting HIVE_TRUST_KEY_ID env var does not affect trust store."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "test-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(pem)
            # Set a misleading env var
            os.environ["HIVE_TRUST_KEY_ID"] = "evil-key"
            try:
                ts = TrustStore.from_pem_file(pem_path)
                # Env var did not inject a key
                assert "evil-key" not in ts.keys
                assert "test-key" in ts.keys
            finally:
                del os.environ["HIVE_TRUST_KEY_ID"]

    def test_trust_store_not_affected_by_env_var_pem(self):
        """Setting HIVE_TRUST_PEM env var does not inject key material."""
        priv = Ed25519PrivateKey.generate()
        pem = export_public_key_pem(priv.public_key(), "test-key")
        with tempfile.TemporaryDirectory() as tmp:
            pem_path = Path(tmp) / "trust.pem"
            pem_path.write_text(pem)
            os.environ["HIVE_TRUST_PEM"] = "fake-pem-data"
            try:
                ts = TrustStore.from_pem_file(pem_path)
                # Only the real key from the file is loaded
                assert "test-key" in ts.keys
                assert len(ts.keys) == 1
            finally:
                del os.environ["HIVE_TRUST_PEM"]

    def test_verify_not_affected_by_env_var_signature(self):
        """Signature verification ignores env vars."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("test-key", export_public_key_pem(priv.public_key(), "test-key"))
        from updates.signing import sign_metadata
        metadata = {
            "schema_version": 1,
            "release": {
                "version": "1.0.0",
                "release_id": "test",
                "commit": "abc",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
            "manifest_digest": "abc123",
        }
        signed = sign_metadata(metadata, priv, "test-key")
        # Tamper attempt via env var
        os.environ["HIVE_SIGNATURE_OVERRIDE"] = "tampered"
        try:
            # Verification still works correctly (env var ignored)
            from updates.signing import verify_metadata
            verify_metadata(signed, ts)  # should succeed
        finally:
            del os.environ["HIVE_SIGNATURE_OVERRIDE"]

    def test_trust_store_init_requires_explicit_dict(self):
        """TrustStore.__init__ requires explicit keys dict, not env var."""
        sig = inspect.signature(TrustStore.__init__)
        params = list(sig.parameters.keys())
        assert "keys" in params
        assert "env_var" not in params
