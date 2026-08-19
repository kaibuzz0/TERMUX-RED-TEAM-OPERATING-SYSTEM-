"""Tests for lib/hive_path.py central path resolution module."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from lib.hive_path import (
    resolve_repository_root,
    load_metadata,
    resolve_canonical_source,
    resolve_canonical_launcher,
    resolve_config_root,
    resolve_state_root,
    resolve_data_root,
    resolve_cache_root,
    resolve_log_root,
    resolve_temp_root,
    resolve_future_state_dirs,
    PathResolutionError,
    CanonicalMetadataError,
    LauncherTypeError,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class RepositoryRootResolutionTests(unittest.TestCase):
    def test_resolve_from_file(self):
        root = resolve_repository_root(REPO_ROOT / "bin" / "hive")
        self.assertTrue((root / "hive-canonical.json").is_file())

    def test_resolve_from_directory(self):
        root = resolve_repository_root(REPO_ROOT / "bin")
        self.assertTrue((root / "hive-canonical.json").is_file())

    def test_resolve_from_parent_directory(self):
        root = resolve_repository_root(REPO_ROOT)
        self.assertTrue((root / "hive-canonical.json").is_file())

    def test_resolve_outside_repo_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PathResolutionError):
                resolve_repository_root(tmp)


class MetadataValidationTests(unittest.TestCase):
    def test_load_real_metadata(self):
        data = load_metadata(REPO_ROOT)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["current_canonical_source"], ".")

    def test_missing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CanonicalMetadataError):
                load_metadata(Path(tmp))

    def test_malformed_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "hive-canonical.json").write_text("not json", encoding="utf-8")
            with self.assertRaises(CanonicalMetadataError):
                load_metadata(Path(tmp))

    def test_unknown_launcher_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = {
                "schema_version": 1,
                "current_canonical_source": "src",
                "current_canonical_launcher": "bin/hive",
                "current_canonical_launcher_type": "perl",
                "launcher_execution_policy": "explicit-interpreter",
            }
            (Path(tmp) / "hive-canonical.json").write_text(json.dumps(metadata), encoding="utf-8")
            (Path(tmp) / "src" / "bin").mkdir(parents=True)
            (Path(tmp) / "src" / "bin" / "hive").write_text("#", encoding="utf-8")
            with self.assertRaises(LauncherTypeError):
                load_metadata(Path(tmp))


class CanonicalPathTests(unittest.TestCase):
    def test_resolve_canonical_source(self):
        source = resolve_canonical_source(REPO_ROOT)
        self.assertTrue(source.is_dir())
        # Post-consolidation canonical source is the repository root.
        self.assertEqual(source.resolve(), REPO_ROOT.resolve())

    def test_resolve_canonical_launcher(self):
        launcher = resolve_canonical_launcher(REPO_ROOT)
        self.assertTrue(launcher.is_file())
        self.assertEqual(launcher.resolve(), (REPO_ROOT / "bin" / "hive").resolve())


class PathRootResolutionTests(unittest.TestCase):
    def test_config_root_default(self):
        root = resolve_config_root(home=Path("/home/test"))
        self.assertEqual(root.as_posix(), "/home/test/.config/hive")

    def test_state_root_default(self):
        root = resolve_state_root(home=Path("/home/test"))
        self.assertEqual(root.as_posix(), "/home/test/.local/state/hive")

    def test_data_root_default(self):
        root = resolve_data_root(home=Path("/home/test"))
        self.assertEqual(root.as_posix(), "/home/test/.local/share/hive")

    def test_cache_root_default(self):
        root = resolve_cache_root(home=Path("/home/test"))
        self.assertEqual(root.as_posix(), "/home/test/.cache/hive")

    def test_log_root_default(self):
        root = resolve_log_root(home=Path("/home/test"))
        self.assertIn("logs", str(root))
        self.assertIn("state", str(root))

    def test_temp_root_default(self):
        root = resolve_temp_root()
        self.assertIn("hive", str(root))

    def test_config_override_must_be_absolute(self):
        import os
        with patch.dict(os.environ, {"HIVE_CONFIG_ROOT": "relative/path"}):
            with self.assertRaises(PathResolutionError):
                resolve_config_root()

    def test_absolute_override_accepted(self):
        import os
        # Use a drive-bearing absolute path on Windows; POSIX absolute elsewhere.
        if os.name == "nt":
            override = "C:\\hive\\config"
            expected = "C:/hive/config"
        else:
            override = "/opt/hive/config"
            expected = "/opt/hive/config"
        with patch.dict(os.environ, {"HIVE_CONFIG_ROOT": override}):
            root = resolve_config_root()
            self.assertEqual(root.as_posix(), expected)

    def test_empty_override_rejected(self):
        import os
        with patch.dict(os.environ, {"HIVE_CONFIG_ROOT": ""}):
            root = resolve_config_root(home=Path("/home/test"))
            self.assertEqual(root.as_posix(), "/home/test/.config/hive")


class FutureStateDirTests(unittest.TestCase):
    def test_future_dirs_do_not_create_filesystem_entries(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        # Use an isolated temporary home so pre-existing system directories do
        # not cause false positives on Windows when HOME is unset.
        tmp_home = Path(tempfile.mkdtemp())
        with patch.dict(os.environ, {"HOME": str(tmp_home)}):
            dirs = resolve_future_state_dirs()
            # Verify none of the paths were created as a side effect.
            # Pre-existing directories (like home) are expected; we only care that
            # function did not create new entries under .config/.local/.cache.
            created_by_function = [
                p for p in dirs.values()
                if p and p.exists() and ".config" in str(p) or (p and p.exists() and ".local" in str(p)) or (p and p.exists() and ".cache" in str(p))
            ]
            self.assertEqual(created_by_function, [])

    def test_home_based_paths(self):
        dirs = resolve_future_state_dirs()
        self.assertIn(".config", str(dirs["config_dir"]))
        self.assertIn("hive", str(dirs["config_dir"]))


if __name__ == "__main__":
    unittest.main()
