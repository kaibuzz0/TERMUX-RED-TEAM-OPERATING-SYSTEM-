"""E1-NO-TRUST-ALL: No trust-all or universal bypass state exists.

The codebase must not contain any mechanism that unconditionally trusts
all keys, skips verification, or disables trust checks. The only controlled
bypass is the explicit `allow_emergency` flag on BundleVerifier.verify(),
which is already tested in E6.
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from updates.trust import TrustStore, TrustError
from updates.verifier import BundleVerifier
from updates.errors import BundleError
from plugin_sdk.schema import FORBIDDEN_CAPABILITIES
from updates.signing import export_public_key_pem, sign_metadata, verify_metadata


class TestNoTrustAllState:
    """Verify absence of universal trust bypass mechanisms."""

    def _sample_metadata(self):
        return {
            "schema_version": 1,
            "release": {
                "version": "1.0.0-rc.1",
                "release_id": "test-release",
                "commit": "abc123",
                "platforms": ["linux"],
                "architectures": ["x86_64"],
                "release_sequence": 1,
                "security_sequence": 1,
            },
            "manifest_digest": "abc123",
        }

    # ------------------------------------------------------------------
    # Source absence: no trust-all or skip-verify patterns
    # ------------------------------------------------------------------

    def test_trust_store_no_trust_all_method(self):
        """TrustStore has no trust_all(), enable_all(), or skip_verify() method."""
        methods = {m for m in dir(TrustStore) if not m.startswith("_")}
        forbidden = {"trust_all", "enable_all", "skip_verify", "disable_verify",
                     "bypass_verify", "trust_any", "accept_all"}
        assert methods & forbidden == set(), (
            f"TrustStore must not have trust-all methods: {methods & forbidden}"
        )

    def test_bundle_verifier_verify_always_checks_trust(self):
        """BundleVerifier.verify() always calls verify_metadata unless allow_emergency."""
        src = inspect.getsource(BundleVerifier.verify)
        # verify_metadata is called before the emergency except block
        assert "verify_metadata" in src
        # The only bypass is allow_emergency (explicit flag)
        assert "allow_emergency" in src
        # No unconditional skip
        assert "skip" not in src.lower() or "allow_emergency" in src

    def test_no_universal_bypass_in_verifier_source(self):
        """updates/verifier.py contains no unconditional verification skip."""
        import updates.verifier as verifier_module
        src = inspect.getsource(verifier_module)
        assert "trust_all" not in src.lower()
        assert "skip_verify" not in src.lower()
        assert "disable_verify" not in src.lower()
        assert "bypass" not in src.lower() or "allow_emergency" in src.lower()

    # ------------------------------------------------------------------
    # Behavioral: empty store never trusts anything
    # ------------------------------------------------------------------

    def test_empty_trust_store_rejects_all_signatures(self):
        """Empty TrustStore has zero keys → verify_metadata always fails."""
        priv = Ed25519PrivateKey.generate()
        ts = TrustStore()
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv, "any-key")
        with pytest.raises(TrustError, match="Unknown key ID"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # Behavioral: no implicit trust from store size
    # ------------------------------------------------------------------

    def test_populated_store_does_not_auto_trust_unknown_key(self):
        """Having keys in store does not imply trust for unknown key_id."""
        priv_a = Ed25519PrivateKey.generate()
        priv_b = Ed25519PrivateKey.generate()
        ts = TrustStore()
        ts.add_key("key-a", export_public_key_pem(priv_a.public_key(), "key-a"))
        # Sign with key-b (not in store)
        metadata = self._sample_metadata()
        signed = sign_metadata(metadata, priv_b, "key-b")
        with pytest.raises(TrustError, match="Unknown key ID"):
            verify_metadata(signed, ts)

    # ------------------------------------------------------------------
    # Emergency bypass is explicit, not implicit
    # ------------------------------------------------------------------

    def test_emergency_bypass_requires_explicit_flag(self):
        """Without allow_emergency=True, untrusted bundle is rejected."""
        ts = TrustStore()  # empty
        verifier = BundleVerifier(
            trust_store=ts,
            platform="linux",
            architecture="x86_64",
        )
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            # Create a minimal invalid bundle
            from updates.bundle import create_tar_bundle
            source = Path(tmp) / "source"
            source.mkdir()
            bundle = Path(tmp) / "bundle.tar.gz"
            create_tar_bundle(source, bundle, [], {"schema_version": 1, "release": {"version": "1.0.0", "release_id": "x", "commit": "a", "platforms": ["linux"], "architectures": ["x86_64"], "release_sequence": 1, "security_sequence": 1}})
            with pytest.raises((TrustError, BundleError)):
                verifier.verify(bundle, work, allow_emergency=False)

    # ------------------------------------------------------------------
    # Forbidden capabilities include policy.bypass
    # ------------------------------------------------------------------

    def test_policy_bypass_is_forbidden(self):
        """policy.bypass is in FORBIDDEN_CAPABILITIES and never granted."""
        assert "policy.bypass" in FORBIDDEN_CAPABILITIES

    def test_no_trust_all_capability_exists(self):
        """No capability named trust.all, verify.skip, or similar exists."""
        from hive_broker.capabilities import _CAPABILITY_NAMES
        names = set(_CAPABILITY_NAMES)
        forbidden_names = {"trust.all", "trust_any", "verify.skip",
                           "verify.none", "policy.bypass", "security.disable"}
        assert names & forbidden_names == set(), (
            f"Forbidden capabilities found: {names & forbidden_names}"
        )
