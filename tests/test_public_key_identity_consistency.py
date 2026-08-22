"""Regression test: active trust-store key/fingerprint matches bootstrap and public docs."""

from __future__ import annotations

import re
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from updates.trust import TrustStore, TRUST_STORE_PATH


def _active_release_key_id_and_fingerprint() -> tuple[str, str]:
    store = TrustStore.from_pem_file(TRUST_STORE_PATH)
    for key_id, trusted in store.keys.items():
        if trusted.status == "active" and trusted.role == "release":
            raw = trusted.public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            import hashlib
            fingerprint = hashlib.sha256(raw).hexdigest()
            return key_id, fingerprint
    raise AssertionError("no active release key in trust store")


def test_bootstrap_root_key_matches_active_trust_store_key():
    from bootstrap import verify_bundle
    active_id, active_fp = _active_release_key_id_and_fingerprint()
    assert verify_bundle.ROOT_KEY_ID == active_id
    assert verify_bundle.ROOT_KEY_FINGERPRINT == active_fp


def test_docs_index_html_current_production_key_matches_active_trust_store():
    repo_root = Path(__file__).with_name("..")
    docs_path = repo_root / "docs" / "index.html"
    text = docs_path.read_text(encoding="utf-8")
    match = re.search(
        r'Key ID:\s*([^<]+)</div>\s*<div class="value">([0-9a-f]+)</div>',
        text,
    )
    assert match, "could not find current production key block in docs/index.html"
    active_id, active_fp = _active_release_key_id_and_fingerprint()
    assert match.group(1).strip() == active_id
    assert match.group(2).strip() == active_fp


def test_no_current_production_block_mentions_revoked_2026_02_fingerprint():
    repo_root = Path(__file__).with_name("..")
    docs_path = repo_root / "docs" / "index.html"
    text = docs_path.read_text(encoding="utf-8")
    revoked_fp = "55c4ca0853756b608c250f687ea8aa3f5ab9157240a243648303185b5f6925f4"
    # The revoked fingerprint may appear in historical evidence, but not as the current production value.
    assert revoked_fp not in text, "docs/index.html still embeds revoked 2026-02 fingerprint"
