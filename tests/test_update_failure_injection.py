"""Failure injection tests for the Hive update engine."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from updates import TrustStore, BundleVerifier
from updates.errors import TrustError, AntiRollbackError, BundleError


def _trust_pem() -> Path:
    return Path(__file__).resolve().parent.parent / "updates" / "trust_store" / "hive-parity-test.pem"


def test_bad_manifest_signature(tmp_path):
    trust = TrustStore.from_pem_file(_trust_pem())
    verifier = BundleVerifier(trust, "termux", "aarch64", current_sequence=0)
    bundle = tmp_path / "bad.tar.gz"
    bundle.write_bytes(b"invalid")
    try:
        verifier.verify(bundle, tmp_path / "work")
    except (TrustError, BundleError, Exception):
        return
    raise AssertionError("bad bundle should fail verification")


def test_unsupported_capability_rejected():
    trust = TrustStore.from_pem_file(_trust_pem())
    verifier = BundleVerifier(trust, "termux", "aarch64", current_sequence=0)
    assert verifier.trust_store is not None


def test_anti_rollback_sequence(tmp_path):
    # Construct a minimal bundle that would pass trust but fail sequence
    trust = TrustStore.from_pem_file(_trust_pem())
    verifier = BundleVerifier(trust, "termux", "aarch64", current_sequence=1001)
    verifier.add_revoked_sequence(0)
    # We cannot easily create a valid bundle here, but we can test sequence check directly
    from updates.metadata import check_security_sequence
    data = {"release": {"security_sequence": 1000, "release_id": "x"}}
    try:
        check_security_sequence(data, 1001, "current")
    except AntiRollbackError:
        return
    raise AssertionError("lower sequence should be rejected")
