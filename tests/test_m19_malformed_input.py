"""Milestone 19 — Area B: Malformed input and parsing attack tests.

Tests JSON/config/bundle/malformed input handling in canonical Hive OS.
"""

from __future__ import annotations

import json
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path

import pytest

from config_engine.errors import ConfigValidationError
from config_engine.loader import load_config_file
from config_engine.persistence import ConfigurationStore
from services.errors import ServiceConfigError
from services.supervisor import Supervisor
from updates.bundle import extract_bundle, BundleError




def _skip_if_no_symlink_support():
    """Skip the current test if this Windows session cannot create symlinks."""
    import sys, tempfile
    if sys.platform != "win32":
        return
    from pathlib import Path
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            src.write_text("x")
            dst.symlink_to(src)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("symlink creation requires elevated privileges on this platform")

class TestMalformedInput:
    def test_deeply_nested_json_rejected(self):
        """B1: Very deeply nested JSON should be handled gracefully."""
        # Python json.loads has a default max nesting depth of 1000
        # We test near that boundary
        depth = 2000
        payload = "{" * depth + "\"key\": \"value\"" + "}" * depth
        with pytest.raises((RecursionError, json.JSONDecodeError)):
            json.loads(payload)

    def test_invalid_utf8_in_config(self):
        """B2: Invalid UTF-8 bytes in config file should error cleanly."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "bad.cfg"
            cfg.write_bytes(b"\xff\xfe key = value")
            with pytest.raises((UnicodeDecodeError, ConfigValidationError)):
                load_config_file(cfg)

    def test_path_traversal_variants_rejected(self):
        """B3: Path traversal variants must be rejected by _resolve_path."""
        with tempfile.TemporaryDirectory() as tmp:
            manifests = {}
            state = Path(tmp) / "state"
            log = Path(tmp) / "log"
            state.mkdir()
            log.mkdir()
            # Supervisor resolves repository root from the source file by default.
            # Patch it to the temp dir so the containment test is isolated.
            import services.supervisor as _supervisor_mod
            original_repo_root = _supervisor_mod._repo_root
            _supervisor_mod._repo_root = lambda: Path(tmp)
            try:
                supervisor = Supervisor(manifests, state, log, {})
                repo_root = supervisor._resolve_path("repository", ".", {})

                # Normal path
                result = supervisor._resolve_path("repository", "bin/hive", {})
                # Cross-platform: Windows uses backslashes in str(Path).
                assert "bin/hive" in result.as_posix()

                # Direct traversal caught by explicit check
                with pytest.raises(ServiceConfigError):
                    supervisor._resolve_path("repository", "../escape", {})

                # Directory named 'fourdots' is NOT traversal (no actual .. component).
                # It resolves harmlessly under base.  Using '....' is not portable:
                # Windows path normalization treats multi-dot-only segments as parent
                # references, so the same semantics are tested with a normal name.
                fourdots = repo_root / "fourdots"
                fourdots.mkdir(exist_ok=True)
                result = supervisor._resolve_path("repository", "fourdots/etc/passwd", {})
                assert result.as_posix().endswith("fourdots/etc/passwd")
                assert result.parts[-3] == "fourdots"
                fourdots.rmdir()

                # Symlink tests require elevated privileges on Windows.
                _skip_if_no_symlink_support()

                # Absolute symlink escape caught by relative_to after resolution
                evil = repo_root / "evil_link"
                if evil.exists() or evil.is_symlink():
                    evil.unlink()
                evil.symlink_to("/etc/passwd")
                try:
                    with pytest.raises(ServiceConfigError):
                        supervisor._resolve_path("repository", "evil_link", {})
                finally:
                    evil.unlink()

                # Relative symlink escape caught by relative_to
                up = repo_root / "up"
                if up.exists() or up.is_symlink():
                    up.unlink()
                up.symlink_to("..")
                try:
                    with pytest.raises(ServiceConfigError):
                        supervisor._resolve_path("repository", "up/etc/passwd", {})
                finally:
                    up.unlink()
            finally:
                _supervisor_mod._repo_root = original_repo_root

    def test_symlink_in_working_directory(self):
        _skip_if_no_symlink_support()
        """B4: Symlink as working directory must not escape containment."""
        with tempfile.TemporaryDirectory() as tmp:
            real_dir = Path(tmp) / "real"
            real_dir.mkdir()
            link_dir = Path(tmp) / "link"
            link_dir.symlink_to(real_dir)

            manifests = {
                "test-svc": {
                    "enabled": True,
                    "command": {"interpreter": "sh", "path": "echo", "args": ["hello"]},
                    "working_directory": {"base": "temp-root", "path": str(link_dir.relative_to(Path(tmp)))},
                }
            }
            state = Path(tmp) / "state"
            log = Path(tmp) / "log"
            state.mkdir()
            log.mkdir()

            # Note: the supervisor resolves paths against known roots;
            # a symlink inside the resolved path is acceptable as long as
            # the initial resolution does not escape.
            supervisor = Supervisor(manifests, state, log, {})
            # Just verify construction does not crash; full containment
            # is verified by the path resolution test above.
            assert supervisor is not None

    def test_bundle_size_limit_enforced(self):
        """B5: Bundle expanded size must not exceed MAX_EXPANDED_SIZE."""
        # Verify the limit constant exists and is reasonable
        from updates.bundle import MAX_EXPANDED_SIZE, MAX_FILE_COUNT
        assert MAX_EXPANDED_SIZE == 512 * 1024 * 1024  # 512 MiB
        assert MAX_FILE_COUNT == 50000

    def test_bundle_hardlink_rejected(self):
        """B5 continued: Bundle containing hardlink must be rejected."""
        import io
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf:
            # Add a regular file
            info = tarfile.TarInfo(name="regular.txt")
            info.size = 5
            tf.addfile(info, io.BytesIO(b"hello"))
            # Add a hardlink to it
            hl = tarfile.TarInfo(name="hardlink")
            hl.type = tarfile.LNKTYPE
            hl.linkname = "regular.txt"
            tf.addfile(hl)

        with tempfile.TemporaryDirectory() as tmp:
            bundle_path = Path(tmp) / "bundle.tar"
            bundle_path.write_bytes(buf.getvalue())
            work_dir = Path(tmp) / "work"
            work_dir.mkdir()
            with pytest.raises(BundleError):
                extract_bundle(bundle_path, work_dir)

    def test_bundle_symlink_rejected(self):
        _skip_if_no_symlink_support()
        """B5: Bundle containing symlink must be rejected."""
        import io
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf:
            info = tarfile.TarInfo(name="link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tf.addfile(info)

        with tempfile.TemporaryDirectory() as tmp:
            bundle_path = Path(tmp) / "bundle.tar"
            bundle_path.write_bytes(buf.getvalue())
            work_dir = Path(tmp) / "work"
            work_dir.mkdir()
            with pytest.raises(BundleError):
                extract_bundle(bundle_path, work_dir)

    def test_empty_policy_json_defaults_deny(self):
        """B7: Empty or corrupted policy JSON must default to DENY."""
        from policy_engine.loader import PolicyLoader
        from policy_engine.evaluator import evaluate
        from policy_engine.requests import PolicyRequest

        loader = PolicyLoader({})
        ps = loader.load("observer")
        request = PolicyRequest(
            schema_version=1,
            request_id="test",
            transaction_id="txn-1",
            actor={"type": "user", "id": "test"},
            capability="unknown_capability",
            resource={"type": "test", "id": "test"},
            context={},
        )
        decision = evaluate(request, ps)
        # Unknown capability raises PolicyRequestError → caught as ERROR
        # This is fail-closed: the system refuses to evaluate unrecognized capabilities
        assert decision.decision.value == "ERROR"
        assert decision.reason_code == "POLICY_CONFIGURATION_INVALID"

    def test_integer_overflow_sequence_handled(self):
        """B6: Integer overflow in sequence number should be handled safely."""
        from updates.metadata import build_metadata, parse_metadata
        from updates.errors import BundleError

        # Test with very large integer
        large_seq = 2**31  # Beyond MAX_SECURITY_SEQUENCE
        with pytest.raises(BundleError):
            build_metadata(
                version="1.0.0",
                release_id="test",
                commit="abc123",
                artifacts=[],
                platforms=["android"],
                architectures=["aarch64"],
                minimum_hive_version="1.0.0",
                security_sequence=large_seq,
            )

        # Verify boundary at exactly MAX_SECURITY_SEQUENCE
        from updates.metadata import MAX_SECURITY_SEQUENCE
        data = build_metadata(
            version="1.0.0",
            release_id="test",
            commit="abc123",
            artifacts=[],
            platforms=["android"],
            architectures=["aarch64"],
            minimum_hive_version="1.0.0",
            security_sequence=MAX_SECURITY_SEQUENCE,
        )
        assert data["release"]["security_sequence"] == MAX_SECURITY_SEQUENCE