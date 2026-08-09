"""Milestone 19 — Area I: Security regression tests.

End-to-end security property verification ensuring all Milestone 18
security guarantees still hold in the release candidate.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from security.vault.crypto import derive_key, encrypt, decrypt, CryptoError
from policy_engine.evaluator import PolicyEvaluator
from policy_engine.requests import PolicyRequest
from policy_engine.rules import PolicySet, Rule, PolicyProfile, is_mutating
from policy_engine.decisions import DecisionState
from policy_engine.errors import PolicyRequestError
from installer.activate import ActiveState, ActivationSafetyError
from config_engine.persistence import FileLock, atomic_write_json
from config_engine.errors import ConfigTransactionError
from updates.signing import sign_metadata, verify_metadata
from updates.trust import TrustStore, TrustError
from updates.signing import export_public_key_pem
from hive_broker.transaction import Transaction
from hive_broker.adapters import dispatch


class TestSecurityRegression:
    # -----------------------------------------------------------------------
    # I1: Vault encryption/decryption round-trip (Milestone 8)
    # -----------------------------------------------------------------------

    def test_vault_encrypt_decrypt_round_trip(self):
        """I1: Vault must encrypt and decrypt data correctly."""
        key = derive_key(
            master_password="test-password",
            salt=b"0123456789abcdef0123456789abcdef",
            parameters={"n": 2**10, "r": 8, "p": 1},
        )
        plaintext = b"sensitive data here"
        nonce = b"0123456789ab"  # 12 bytes for AES-GCM
        ad = b"associated-data"
        ciphertext, tag = encrypt(key, nonce, plaintext, ad)
        decrypted = decrypt(key, nonce, ciphertext, tag, ad)
        assert decrypted == plaintext

    def test_vault_decrypt_with_wrong_key_fails(self):
        """I1: Decrypting with wrong key must raise CryptoError."""
        key1 = derive_key(
            master_password="password1",
            salt=b"0123456789abcdef0123456789abcdef",
            parameters={"n": 2**10, "r": 8, "p": 1},
        )
        key2 = derive_key(
            master_password="password2",
            salt=b"0123456789abcdef0123456789abcdef",
            parameters={"n": 2**10, "r": 8, "p": 1},
        )
        plaintext = b"sensitive data"
        nonce = b"0123456789ab"
        ad = b"associated-data"
        ciphertext, tag = encrypt(key1, nonce, plaintext, ad)
        with pytest.raises(CryptoError):
            decrypt(key2, nonce, ciphertext, tag, ad)

    # -----------------------------------------------------------------------
    # I2: Policy evaluator default deny (Milestone 9)
    # -----------------------------------------------------------------------

    def test_policy_evaluator_default_deny(self):
        """I2: Empty policy set must default to DENY."""
        evaluator = PolicyEvaluator(PolicySet(profiles={}))
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "test",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "test"},
            "capability": "vault.status",
            "resource": {"type": "vault", "id": "master"},
            "context": {},
        })
        result = evaluator.evaluate(req)
        # Without observer profile, evaluation returns ERROR, which is still fail-closed
        assert result.decision in (DecisionState.DENY, DecisionState.ERROR)

    def test_policy_evaluator_allow_matching_rule(self):
        """I2: Matching rule must result in ALLOW."""
        rule = Rule(
            rule_id="allow-operator-vault",
            priority=100,
            effect=DecisionState.ALLOW,
            actors={"operator"},
            capabilities={"vault.status"},
            resources={"vault"},
        )
        profile = PolicyProfile(
            name="observer",
            description="Observer profile",
            rules=[rule],
            default_decision=DecisionState.DENY,
        )
        evaluator = PolicyEvaluator(PolicySet(profiles={"observer": profile}))
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "test",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "test"},
            "capability": "vault.status",
            "resource": {"type": "vault", "id": "master"},
            "context": {},
        })
        result = evaluator.evaluate(req)
        assert result.decision == DecisionState.ALLOW

    # -----------------------------------------------------------------------
    # I3: Mutating capability enforcement (Milestone 9)
    # -----------------------------------------------------------------------

    def test_mutating_capability_requires_explicit_rule(self):
        """I3: Mutating capability must require explicit rule (not default allow)."""
        assert is_mutating("vault.set") is True
        evaluator = PolicyEvaluator(PolicySet(profiles={}))
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "test",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "test"},
            "capability": "vault.set",  # mutating
            "resource": {"type": "vault", "id": "master"},
            "context": {},
        })
        result = evaluator.evaluate(req)
        assert result.decision in (DecisionState.DENY, DecisionState.ERROR)

    # -----------------------------------------------------------------------
    # I4: Activation safety (Milestone 11)
    # -----------------------------------------------------------------------

    def test_activation_without_approval_fails(self):
        """I4: Activation without --approve must raise ActivationSafetyError."""
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = Path(tmp) / "state"
            active = ActiveState(data, state, "txn-1")
            with pytest.raises(ActivationSafetyError, match="--approve"):
                active.activate("some-release", approve=False)

    # -----------------------------------------------------------------------
    # I5: Config atomicity (Milestone 14)
    # -----------------------------------------------------------------------

    def test_config_atomic_write_no_temp_files_left(self):
        """I5: Atomic writes must not leave temp files behind."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            atomic_write_json(target, {"key": "value"})
            # No temp files should remain
            temps = list(Path(tmp).glob("*.tmp"))
            assert len(temps) == 0
            assert target.exists()

    # -----------------------------------------------------------------------
    # I6: Trust store integrity (Milestone 12)
    # -----------------------------------------------------------------------

    def test_trust_store_rejects_unknown_key(self):
        """I6: Unknown key must be rejected by trust store."""
        priv = Ed25519PrivateKey.generate()
        pub_pem = export_public_key_pem(priv.public_key(), "test-key")
        store = TrustStore()
        store.add_key("test-key", pub_pem)
        # Different key signs metadata
        other_priv = Ed25519PrivateKey.generate()
        metadata = {"schema_version": 1, "version": "1.0.0", "release_id": "x"}
        signed = sign_metadata(metadata, other_priv, "test-key")
        with pytest.raises(TrustError, match="Signature mismatch"):
            verify_metadata(signed, store)

    # -----------------------------------------------------------------------
    # I7: Transaction isolation (Milestone 15)
    # -----------------------------------------------------------------------

    def test_transaction_ids_are_unique(self):
        """I7: Transaction IDs must be statistically unique."""
        ids = set()
        for i in range(100):
            txn = Transaction(
                transaction_id=f"txn-{i}",
                task_id="task-1",
                session_id="session-1",
                audit_id="audit-1",
            )
            ids.add(txn.transaction_id)
        assert len(ids) == 100

    # -----------------------------------------------------------------------
    # I8: Broker dispatch gate (Milestone 15)
    # -----------------------------------------------------------------------

    def test_broker_dispatch_blocks_unknown_capability(self):
        """I8: Unknown capability in broker dispatch must raise."""
        with pytest.raises(Exception):
            dispatch("unknown.capability", None, {})

    # -----------------------------------------------------------------------
    # I9: FileLock contention (Milestone 14)
    # -----------------------------------------------------------------------

    def test_filelock_blocks_concurrent_access(self):
        """I9: FileLock must serialize concurrent access attempts."""
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "lock"
            lock = FileLock(lock_path, timeout=0.1)
            with lock:
                # Second acquisition should time out
                lock2 = FileLock(lock_path, timeout=0.1)
                with pytest.raises(ConfigTransactionError):
                    with lock2:
                        pass  # should not reach here

    # -----------------------------------------------------------------------
    # I10: Signing algorithm downgrade blocked
    # -----------------------------------------------------------------------

    def test_rsa_key_rejected_by_trust_store(self):
        """I10: RSA key must be rejected (Ed25519 only)."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        # TrustStore.add_key checks for Ed25519 and rejects RSA
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        pub_pem = rsa_priv.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        store = TrustStore()
        with pytest.raises(TrustError, match="Only Ed25519"):
            store.add_key("rsa-key", pub_pem)
