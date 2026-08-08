"""Verify canonical manifest bytes are hashed by manifest_digest().

The security property is: manifest_digest() produces a deterministic digest
by serializing entries to canonical JSON bytes (sorted keys, no ASCII escapes,
minimal separators) and then hashing those bytes with SHA-256.

These tests verify:
1. Equivalent manifests with different key order produce identical canonical bytes
2. Equivalent manifests with different whitespace produce identical canonical bytes
3. The canonical bytes are actually what gets hashed (not some other representation)
4. Non-equivalent manifests (different values) produce different canonical bytes
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from release_engine.manifest import manifest_digest


class TestCanonicalManifestBytesHashed:

    def test_key_order_invariance(self):
        """Different key order in entries must produce identical digest."""
        m1 = [{"path": "a.py", "hash": "abc", "size": "1"}]
        m2 = [{"hash": "abc", "path": "a.py", "size": "1"}]
        m3 = [{"size": "1", "hash": "abc", "path": "a.py"}]

        d1 = manifest_digest(m1)
        d2 = manifest_digest(m2)
        d3 = manifest_digest(m3)

        assert d1 == d2 == d3, "Canonical form should normalize key order"

    def test_list_order_preserved(self):
        """Entry order in the list must affect digest (list order is significant)."""
        m1 = [{"path": "a.py"}, {"path": "b.py"}]
        m2 = [{"path": "b.py"}, {"path": "a.py"}]

        d1 = manifest_digest(m1)
        d2 = manifest_digest(m2)

        assert d1 != d2, "List order should be significant"

    def test_canonical_bytes_match_hashlib(self):
        """manifest_digest must equal hashlib.sha256 of canonical JSON bytes."""
        entries = [{"path": "bin/hive", "hash": "abc123"}]

        # Compute via manifest_digest
        digest_from_function = manifest_digest(entries)

        # Compute manually: same canonical serialization
        canonical = json.dumps(entries, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        canonical_bytes = canonical.encode("utf-8")
        digest_manual = hashlib.sha256(canonical_bytes).hexdigest()

        assert digest_from_function == digest_manual

    def test_whitespace_invariance(self):
        """Pretty-printed vs compact JSON of same data must produce same digest."""
        # Same logical data, different whitespace
        raw_pretty = '[\n  {\n    "path": "a.py",\n    "hash": "abc"\n  }\n]'
        raw_compact = '[{"path":"a.py","hash":"abc"}]'

        entries_pretty = json.loads(raw_pretty)
        entries_compact = json.loads(raw_compact)

        d_pretty = manifest_digest(entries_pretty)
        d_compact = manifest_digest(entries_compact)

        assert d_pretty == d_compact, "Whitespace should be normalized away"

    def test_unicode_not_escaped(self):
        """Unicode characters should not be escaped in canonical form."""
        m1 = [{"path": "文件.py", "hash": "abc"}]
        # Use json.loads to decode JSON unicode escapes into actual characters
        m2 = [{"path": json.loads('"\\u6587\\u4ef6.py"'), "hash": "abc"}]

        # After json.loads, both should be the same string
        assert m1[0]["path"] == m2[0]["path"]

        d1 = manifest_digest(m1)
        d2 = manifest_digest(m2)

        assert d1 == d2, "Unicode escape differences should be normalized"

    def test_value_difference_changes_digest(self):
        """Different values must produce different canonical bytes and digest."""
        m1 = [{"path": "a.py", "hash": "abc"}]
        m2 = [{"path": "a.py", "hash": "def"}]
        m3 = [{"path": "b.py", "hash": "abc"}]

        d1 = manifest_digest(m1)
        d2 = manifest_digest(m2)
        d3 = manifest_digest(m3)

        assert d1 != d2
        assert d1 != d3
        assert d2 != d3

    def test_separator_normalization(self):
        """JSON with spaces after separators must be normalized."""
        # Python's json.dumps with default separators adds spaces
        raw_with_spaces = '[{"path": "a.py", "hash": "abc"}]'
        raw_no_spaces = '[{"path":"a.py","hash":"abc"}]'

        entries_with = json.loads(raw_with_spaces)
        entries_no = json.loads(raw_no_spaces)

        d_with = manifest_digest(entries_with)
        d_no = manifest_digest(entries_no)

        assert d_with == d_no, "Separator spaces should be normalized"
