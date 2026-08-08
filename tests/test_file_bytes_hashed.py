"""Verify complete file bytes are hashed during manifest and bundle digest computation.

Properties tested:
- _sha256(path) reads full file content in binary mode (not just metadata)
- compute_bundle_digest(path) covers entire file bytes
- Changing a single byte changes the digest
- Truncating a file changes the digest
- Appending bytes changes the digest
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from release_engine.reproducibility import compute_bundle_digest
from updates.manifest import _sha256


class TestCompleteFileBytesHashed:

    def test_sha256_reads_full_file_content(self):
        """_sha256 must hash complete file bytes, not just name or metadata."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.bin"
            content = b"A" * 100000  # 100 KB, larger than 64KB chunk size
            f.write_bytes(content)

            digest = _sha256(f)
            expected = hashlib.sha256(content).hexdigest()
            assert digest == expected

    def test_compute_bundle_digest_reads_full_file(self):
        """compute_bundle_digest must hash complete file bytes."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "bundle.tar.gz"
            content = b"x" * 200000  # 200 KB
            f.write_bytes(content)

            digest = compute_bundle_digest(f)
            expected = hashlib.sha256(content).hexdigest()
            assert digest == expected

    def test_single_byte_change_changes_digest(self):
        """Changing one byte in a file must produce a different digest."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.bin"
            content = b"Hello World!"
            f.write_bytes(content)
            d1 = _sha256(f)

            # Flip one byte
            modified = bytearray(content)
            modified[0] ^= 0xFF
            f.write_bytes(bytes(modified))
            d2 = _sha256(f)

            assert d1 != d2

    def test_truncate_changes_digest(self):
        """Truncating a file must change its digest."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.bin"
            f.write_bytes(b"0123456789abcdef")
            d1 = _sha256(f)

            f.write_bytes(b"0123456789")  # truncated
            d2 = _sha256(f)

            assert d1 != d2

    def test_append_changes_digest(self):
        """Appending bytes to a file must change its digest."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.bin"
            f.write_bytes(b"base content")
            d1 = _sha256(f)

            f.write_bytes(b"base content and more")
            d2 = _sha256(f)

            assert d1 != d2

    def test_chunked_read_matches_single_read(self):
        """_sha256 chunked reading must match hashlib.sha256(single_read)."""
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.bin"
            # Content larger than the 64KB chunk size used in _sha256
            content = bytes(range(256)) * 300  # ~76 KB
            f.write_bytes(content)

            chunked = _sha256(f)
            single = hashlib.sha256(content).hexdigest()
            assert chunked == single
