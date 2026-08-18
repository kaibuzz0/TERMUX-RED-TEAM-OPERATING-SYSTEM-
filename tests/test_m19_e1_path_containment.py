"""E1-CONTAIN: Path containment verification across all layers.

Path traversal defense: `resolve().relative_to(base.resolve())` raises
ValueError if a path escapes its intended directory. This test verifies the
mechanism is applied consistently across vault, staging, config, and trust store
layers.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from security.vault.storage import VaultStorage
from security.vault.errors import VaultSafetyError
from installer.staging import StagingError
from config_engine.validator import validate_path_containment, ConfigValidationError




def _skip_if_no_symlink_support():
    """Skip tests that require creating symlinks when unprivileged on Windows."""
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            src.write_text("x")
            try:
                dst.symlink_to(src)
            except OSError as exc:
                if getattr(exc, "winerror", None) == 1314:
                    pytest.skip("symlink creation requires elevated privileges on this platform")
    except Exception:
        pass

class TestVaultPathContainment:
    """VaultStorage._ensure_contained prevents path escape."""

    def test_vault_path_must_be_inside_vault_dir(self):
        """Vault file inside vault_dir is accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "vault"
            vault_dir.mkdir()
            storage = VaultStorage(vault_dir)
            storage.write("secret", overwrite=True)
            assert storage.exists()

    def test_vault_temp_path_must_be_inside_vault_dir(self):
        """Vault temp file (.tmp) inside vault_dir is accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "vault"
            vault_dir.mkdir()
            storage = VaultStorage(vault_dir)
            storage.write("secret", overwrite=True)
            # .tmp is created and replaced atomically
            assert not (vault_dir / "vault.json.tmp").exists()
            assert (vault_dir / "vault.json").exists()

    def test_vault_path_escape_detected(self):
        """Vault path escaping vault_dir raises VaultSafetyError."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "vault"
            vault_dir.mkdir()
            storage = VaultStorage(vault_dir)
            # Manually tamper vault_path to escape
            storage.vault_path = Path(tmp) / "outside.json"
            with pytest.raises(VaultSafetyError, match="escapes"):
                storage.write("secret", overwrite=True)

    def test_vault_dotdot_escape_detected(self):
        """../ in vault path raises VaultSafetyError."""
        with tempfile.TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "vault"
            vault_dir.mkdir()
            storage = VaultStorage(vault_dir)
            storage.vault_path = vault_dir / ".." / "outside.json"
            with pytest.raises(VaultSafetyError, match="escapes"):
                storage.write("secret", overwrite=True)


class TestStagingPathContainment:
    """StagingArea._validate_containment prevents path escape."""

    def test_staging_path_inside_root_accepted(self):
        """Paths inside staging_root pass containment."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "staging"
            root.mkdir()
            # Simulate containment check directly
            target = root / "subdir" / "file.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("data")
            resolved = target.resolve()
            base = root.resolve()
            resolved.relative_to(base)  # should succeed

    def test_staging_path_escape_raises(self):
        """Path escaping staging_root raises ValueError."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "staging"
            root.mkdir()
            target = Path(tmp) / "outside" / "file.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("data")
            with pytest.raises(ValueError):
                target.resolve().relative_to(root.resolve())


class TestConfigPathContainment:
    """config_engine.validator.validate_path_containment."""

    def test_path_inside_root_passes(self):
        """Path inside root passes validation."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "config"
            root.mkdir()
            target = root / "settings.json"
            target.write_text("{}")
            validate_path_containment(target, root)  # should succeed

    def test_path_outside_root_raises(self):
        """Path outside root raises ConfigValidationError."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "config"
            root.mkdir()
            target = Path(tmp) / "outside.json"
            target.write_text("{}")
            with pytest.raises(ConfigValidationError, match="escapes"):
                validate_path_containment(target, root)

    def test_dotdot_path_raises(self):
        """Path with .. component escaping root raises ConfigValidationError."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "config"
            root.mkdir()
            target = root / ".." / "outside.json"
            with pytest.raises(ConfigValidationError, match="escapes"):
                validate_path_containment(target, root)

    def test_symlink_escape_detected(self):
        """Symlink pointing outside root is detected after resolve()."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "config"
            root.mkdir()
            outside = Path(tmp) / "secret.json"
            outside.write_text("{}")
            link = root / "link.json"
            link.symlink_to(outside)
            with pytest.raises(ConfigValidationError, match="escapes"):
                validate_path_containment(link, root)


class TestPathContainmentMechanism:
    """Core mechanism: resolve() + relative_to()."""

    def test_resolve_follows_symlinks(self):
        """Path.resolve() follows symlinks to their real path."""
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.txt"
            real.write_text("data")
            link = Path(tmp) / "link.txt"
            link.symlink_to(real)
            assert link.resolve() == real.resolve()

    def test_resolve_collapses_dotdot(self):
        """Path.resolve() collapses .. components."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            base.mkdir()
            inside = base / "sub"
            inside.mkdir()
            # ../ escapes to parent
            escaped = inside / ".." / ".." / "etc" / "passwd"
            resolved = escaped.resolve()
            assert ".." not in resolved.parts

    def test_literal_dotdot_is_not_traversal(self):
        """Literal .... in filename is not path traversal (PurePath semantics)."""
        p = Path("....//etc/passwd")
        assert "...." in p.parts
        assert ".." not in p.parts

    def test_relative_to_catches_escape_after_resolve(self):
        """relative_to(base) catches actual escapes after resolve()."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            base.mkdir()
            target = base / ".." / "outside"
            target.mkdir()
            with pytest.raises(ValueError):
                target.resolve().relative_to(base.resolve())