"""Tests for Hive OS canonical source declaration.

These tests use only the Python standard library so they can run without
installing third-party packages. They validate static repository facts, not
runtime behavior.
"""

import json
import os
import sys
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_JSON = REPO_ROOT / "hive-canonical.json"
KNOWN_DUPLICATES = REPO_ROOT / "tests" / "fixtures" / "canonical-source" / "known-duplicates.json"
EXPECTED_REMOTE = "https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-"


class CanonicalSourceTests(unittest.TestCase):
    """Validate the canonical source declaration."""

    def test_canonical_json_exists(self):
        self.assertTrue(CANONICAL_JSON.is_file(), "hive-canonical.json must exist")

    def test_canonical_json_is_valid_json(self):
        with open(CANONICAL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_schema_version(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        self.assertEqual(data.get("schema_version"), 1)

    def test_current_canonical_source_directory_exists(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        source = data.get("current_canonical_source")
        self.assertTrue(
            (REPO_ROOT / source).is_dir(),
            f"current canonical source must exist as a directory: {source}",
        )

    def test_reference_sources_exist(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        refs = data.get("reference_sources", [])
        self.assertIsInstance(refs, list)
        for ref in refs:
            self.assertTrue(
                (REPO_ROOT / ref).is_dir(),
                f"reference source must exist as a directory: {ref}",
            )

    def test_future_target_runtime_is_not_current_source(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        current = data.get("current_canonical_source")
        future = data.get("future_target_runtime")
        self.assertNotEqual(
            current, future, "future target runtime must not be the current source"
        )
        # core/ must not exist yet; if it does, the declaration is stale
        self.assertFalse(
            (REPO_ROOT / future).is_dir(),
            "future target runtime tree must not exist as production runtime yet",
        )


    def test_current_canonical_launcher_exists(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        launcher = data.get("current_canonical_launcher")
        self.assertIsInstance(launcher, str)
        self.assertTrue(
            (REPO_ROOT / launcher).is_file(),
            f"current canonical launcher must exist: {launcher}",
        )

    def test_current_canonical_launcher_inside_canonical_source(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        source = data.get("current_canonical_source")
        launcher = data.get("current_canonical_launcher")
        self.assertTrue(
            str(Path(launcher)).startswith(str(Path(source))),
            f"launcher {launcher} must be inside canonical source {source}",
        )

    def test_no_absolute_paths_in_canonical_launcher(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        launcher = data.get("current_canonical_launcher")
        self.assertFalse(Path(launcher).is_absolute(), "launcher path must be relative")
        self.assertNotIn("\\", launcher, "launcher path must use forward slashes")

    def test_repository_url_matches_expected_remote(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        self.assertEqual(data.get("repository"), EXPECTED_REMOTE)

    def test_no_absolute_personal_paths(self):
        """Metadata must not contain Windows drive letters or absolute home paths."""
        text = CANONICAL_JSON.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"[A-Za-z]:\\", "must not contain Windows paths")
        self.assertNotRegex(text, r"/home/[^/\"/]+", "must not contain absolute home paths")
        self.assertNotRegex(text, r"C:\\Users\\", "must not contain Windows user paths")

    def test_no_secret_like_fields(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        forbidden = {"password", "token", "secret", "key", "api_key", "pin"}
        for field in forbidden:
            self.assertNotIn(
                field,
                data,
                f"metadata must not contain secret-like field: {field}",
            )

    def test_no_duplicate_metadata_file(self):
        """Only one canonical metadata file should exist at the repository root."""
        matches = list(REPO_ROOT.glob("hive-canonical*.json"))
        self.assertEqual(len(matches), 1, "there must be exactly one hive-canonical*.json file")

    def test_generated_flag_is_false(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        self.assertIs(data.get("generated"), False)

    def test_declared_migration_state(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        self.assertEqual(data.get("migration_state"), "canonical-source-declared-interpreter-proven")

    def test_runtime_validation_label(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        self.assertEqual(data.get("runtime_validation"), "unverified-on-termux")

    def test_entrypoint_status_is_pending(self):
        data = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
        self.assertEqual(data.get("entrypoint_status"), "existing-entrypoints-pending-consolidation")

    def test_deterministic_output(self):
        """The JSON file must be deterministic for reproducible tests."""
        text = CANONICAL_JSON.read_text(encoding="utf-8")
        # No timestamps, no absolute paths, no generated identifiers
        self.assertNotRegex(text, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertNotRegex(text, r"[A-Za-z]:\\")


class DuplicateEntrypointDebtTests(unittest.TestCase):
    """Track known duplicate entrypoints as migration debt.

    This test does not require all duplicates to be removed in Milestone 1.
    It fails only if a new undocumented duplicate is introduced.
    """

    def test_known_duplicates_fixture_exists(self):
        self.assertTrue(KNOWN_DUPLICATES.is_file(), "known-duplicates fixture must exist")

    def test_no_new_undocumented_duplicates(self):
        fixture = json.loads(KNOWN_DUPLICATES.read_text(encoding="utf-8"))
        known = fixture.get("known_duplicates", {})

        # Re-scan repository for candidate duplicate entrypoint names
        candidate_names = {"hive", "hive-os", "hive-ctrl", "hive-secure-login",
                           "hive-ui-v2", "hive-gateway", "hive-orchestrator",
                           "hive-hermes", "install-termux", "install", "update",
                           "emergency-repair"}
        found = {name: [] for name in candidate_names}
        for root, dirs, files in os.walk(REPO_ROOT):
            # Skip .git and blueprints
            dirs[:] = [d for d in dirs if d not in {".git", "blueprints", "tests"}]
            for f in files:
                base = os.path.splitext(f)[0]
                if base in candidate_names:
                    full = Path(root) / f
                    # Only count executables or shell scripts. On Windows,
                    # os.access(X_OK) is always true, so restrict to known
                    # script extensions there (HRA-008).
                    if sys.platform == "win32":
                        is_entrypoint = full.suffix in {".sh", ".py"}
                    else:
                        is_entrypoint = full.suffix in {".sh", ".py"} or os.access(full, os.X_OK)
                    if is_entrypoint:
                        found[base].append(str(full.relative_to(REPO_ROOT)).replace(os.sep, "/"))

        # Build set of known paths
        known_paths = set()
        for paths in known.values():
            known_paths.update(paths)

        # Find new undocumented duplicates
        new_duplicates = {}
        for name, paths in found.items():
            if len(paths) > 1:
                new = [p for p in paths if p not in known_paths]
                if new:
                    new_duplicates[name] = new

        self.assertEqual(
            new_duplicates,
            {},
            "new undocumented duplicate entrypoints were introduced; update the fixture or remove the duplicates",
        )


if __name__ == "__main__":
    unittest.main()
