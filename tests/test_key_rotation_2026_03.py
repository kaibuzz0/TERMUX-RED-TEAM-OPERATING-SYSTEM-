"""Regression tests for production key rotation to hive-release-prod-2026-03."""

from __future__ import annotations

from pathlib import Path

import pytest

from cryptography.hazmat.primitives import serialization
from updates.trust import TrustStore, TRUST_STORE_PATH
from updates.errors import TrustError


def test_trust_store_has_three_keys():
    store = TrustStore.from_pem_file(TRUST_STORE_PATH)
    assert "hive-release-prod-2026-01" in store.keys
    assert "hive-release-prod-2026-02" in store.keys
    assert "hive-release-prod-2026-03" in store.keys


def test_2026_01_is_revoked():
    store = TrustStore.from_pem_file(TRUST_STORE_PATH)
    meta = store.keys["hive-release-prod-2026-01"].inspect()
    assert meta["status"] == "revoked"


def test_2026_02_is_revoked():
    store = TrustStore.from_pem_file(TRUST_STORE_PATH)
    meta = store.keys["hive-release-prod-2026-02"].inspect()
    assert meta["status"] == "revoked"
    assert meta.get("replacement_key_id") == "hive-release-prod-2026-03"


def test_2026_03_is_active():
    store = TrustStore.from_pem_file(TRUST_STORE_PATH)
    meta = store.keys["hive-release-prod-2026-03"].inspect()
    assert meta["status"] == "active"
    assert meta["purpose"] == "release"


def test_2026_03_fingerprint_matches_embedded_public_key():
    store = TrustStore.from_pem_file(TRUST_STORE_PATH)
    key = store.keys["hive-release-prod-2026-03"]
    raw = key.public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    import hashlib
    assert hashlib.sha256(raw).hexdigest() == key.fingerprint


def test_revoked_2026_02_cannot_verify_current_release():
    """A dummy release signed by 2026-02 must be rejected."""
    store = TrustStore.from_pem_file(TRUST_STORE_PATH)
    metadata = {
        "release": {"release_id": "hive-os-1.1.0-rc.2-test"},
        "manifest_digest": "0" * 64,
        "signing": {
            "algorithm": "Ed25519",
            "key_id": "hive-release-prod-2026-02",
            "signature": "dGVzdA==",
        },
    }
    with pytest.raises(TrustError):
        from updates.signing import verify_metadata
        verify_metadata(metadata, store)


def test_no_private_key_in_trust_store():
    text = TRUST_STORE_PATH.read_text(encoding="utf-8")
    assert "PRIVATE KEY" not in text
    assert "BEGIN ENCRYPTED PRIVATE KEY" not in text
