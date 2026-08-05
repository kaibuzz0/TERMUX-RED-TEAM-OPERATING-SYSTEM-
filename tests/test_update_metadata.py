"""Tests for release metadata format and validation."""

from __future__ import annotations

import unittest

from updates.metadata import build_metadata, parse_metadata, check_compatibility, check_security_sequence
from updates.errors import BundleError, CompatibilityError, AntiRollbackError


class MetadataTests(unittest.TestCase):
    def test_valid_metadata(self):
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["termux"], ["aarch64"], "0.1.0")
        parsed = parse_metadata(json_text(meta))
        self.assertEqual(parsed["release"]["version"], "1.0.0")

    def test_unknown_schema(self):
        with self.assertRaises(BundleError):
            parse_metadata('{"schema_version": 999}')

    def test_unsupported_platform(self):
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["linux"], ["aarch64"], "0.1.0")
        with self.assertRaises(CompatibilityError):
            check_compatibility(meta, "termux", "aarch64")

    def test_unsupported_architecture(self):
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["termux"], ["x86_64"], "0.1.0")
        with self.assertRaises(CompatibilityError):
            check_compatibility(meta, "termux", "aarch64")

    def test_anti_rollback(self):
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["termux"], ["aarch64"], "0.1.0", security_sequence=5)
        with self.assertRaises(AntiRollbackError):
            check_security_sequence(meta, 10)


def json_text(meta):
    import json
    return json.dumps(meta)


    def test_negative_sequence_rejected(self):
        with self.assertRaises(BundleError):
            build_metadata("1.0.0", "rel-1", "abc", [], ["termux"], ["aarch64"], "0.1.0", security_sequence=-1)

    def test_oversized_sequence_rejected(self):
        with self.assertRaises(BundleError):
            build_metadata("1.0.0", "rel-1", "abc", [], ["termux"], ["aarch64"], "0.1.0", security_sequence=10_000_000_000)

    def test_equal_sequence_same_release_allowed(self):
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["termux"], ["aarch64"], "0.1.0", security_sequence=5)
        # Replaying the same release identity at the same sequence should not raise.
        check_security_sequence(meta, current_sequence=5, current_release_id="rel-1")

    def test_equal_sequence_conflicting_release_rejected(self):
        meta = build_metadata("1.0.0", "rel-2", "abc", [], ["termux"], ["aarch64"], "0.1.0", security_sequence=5)
        with self.assertRaises(AntiRollbackError):
            check_security_sequence(meta, current_sequence=5, current_release_id="rel-1")

    def test_sequence_uses_integers(self):
        meta = build_metadata("1.0.0", "rel-1", "abc", [], ["termux"], ["aarch64"], "0.1.0", security_sequence=10)
        # String "10" must not parse as valid.
        raw = json_text(meta).replace('"security_sequence": 10', '"security_sequence": "10"')
        with self.assertRaises(BundleError):
            parse_metadata(raw)


if __name__ == "__main__":
    unittest.main()
