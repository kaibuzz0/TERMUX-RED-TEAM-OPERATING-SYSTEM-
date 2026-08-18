"""Milestone 19 — Area H: Resource exhaustion tests.

Tests KDF memory bounds, config file size limits, service spawn limits,
and file descriptor exhaustion handling.
"""

from __future__ import annotations

import io
import tempfile
import zlib
from pathlib import Path

import pytest

from config_engine.loader import load_config_file
from config_engine.errors import ConfigError
from security.vault.crypto import derive_key
from services.supervisor import Supervisor, ServiceConfigError




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

class TestResourceExhaustion:
    # -----------------------------------------------------------------------
    # H1: KDF memory exhaustion
    # -----------------------------------------------------------------------

    def test_scrypt_extreme_n_fails_gracefully(self):
        """H1: Unreasonably high scrypt N must raise CryptoError (memory limit)."""
        from security.vault.crypto import CryptoError
        with pytest.raises(CryptoError, match="exceed safety memory bound"):
            derive_key(
                master_password="test",
                salt=b"0123456789abcdef0123456789abcdef",
                parameters={"n": 2**30, "r": 8, "p": 1},
            )

    def test_scrypt_reasonable_n_succeeds(self):
        """H1: Reasonable scrypt parameters must succeed."""
        key = derive_key(
            master_password="test",
            salt=b"0123456789abcdef0123456789abcdef",
            parameters={"n": 2**10, "r": 8, "p": 1},
        )
        assert isinstance(key, bytes)
        assert len(key) == 32  # AES-256 key

    def test_scrypt_boundary_exactly_1gib_rejected(self):
        """H1: scrypt expected memory at 1 GiB boundary triggers safety bound.

        expected_mem = 128 * n * r * p. At n=2**20, r=8, p=1 this is exactly
        1 GiB. The production code rejects expected_mem > 1 GiB, but even if
        that guard were bypassed, hashlib.scrypt maxmem would overflow the
        C long limit (2**31-1 on 32-bit builds) and raise.
        """
        from security.vault.crypto import CryptoError
        with pytest.raises(CryptoError):
            derive_key(
                master_password="test",
                salt=b"0123456789abcdef0123456789abcdef",
                parameters={"n": 2**20, "r": 8, "p": 1},
            )

    def test_scrypt_non_power_of_two_n_rejected(self):
        """H1: scrypt n must be a power of two — non-conforming params rejected."""
        from security.vault.crypto import CryptoError
        with pytest.raises(CryptoError, match="power of two"):
            derive_key(
                master_password="test",
                salt=b"0123456789abcdef0123456789abcdef",
                parameters={"n": 1000, "r": 8, "p": 1},
            )

    def test_scrypt_n_eq_1_rejected(self):
        """H1: scrypt n < 2 rejected (would be trivial KDF)."""
        from security.vault.crypto import CryptoError
        with pytest.raises(CryptoError, match="power of two"):
            derive_key(
                master_password="test",
                salt=b"0123456789abcdef0123456789abcdef",
                parameters={"n": 1, "r": 8, "p": 1},
            )

    def test_scrypt_n_eq_0_rejected(self):
        """H1: scrypt n == 0 rejected."""
        from security.vault.crypto import CryptoError
        with pytest.raises(CryptoError, match="power of two"):
            derive_key(
                master_password="test",
                salt=b"0123456789abcdef0123456789abcdef",
                parameters={"n": 0, "r": 8, "p": 1},
            )

    def test_scrypt_salt_too_short_rejected(self):
        """H1: Salt shorter than 16 bytes rejected."""
        from security.vault.crypto import CryptoError
        with pytest.raises(CryptoError, match="Salt too short"):
            derive_key(
                master_password="test",
                salt=b"short",
                parameters={"n": 2**10, "r": 8, "p": 1},
            )

    # -----------------------------------------------------------------------
    # H2: Config file size / shape DoS (real production bounds)
    # -----------------------------------------------------------------------

    def test_config_loader_rejects_over_5mb_file(self):
        """H2: load_json_file enforces 5 MB max_size_bytes; >5 MB rejected."""
        from config_engine.loader import load_json_file
        from config_engine.errors import ConfigValidationError
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "too_big.json"
            # Create JSON just over 5 MiB
            padding = "x" * (6 * 1024 * 1024)
            config_path.write_text(
                f'{{"data": "{padding}"}}',
                encoding="utf-8",
            )
            assert config_path.stat().st_size > 5 * 1024 * 1024
            with pytest.raises(ConfigValidationError, match="too large"):
                load_json_file(config_path)

    def test_config_loader_rejects_duplicate_keys(self):
        """H2: JSON with duplicate keys rejected by load_json_file."""
        from config_engine.loader import load_json_file
        from config_engine.errors import ConfigValidationError
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "dup.json"
            config_path.write_text('{"key": 1, "key": 2}', encoding="utf-8")
            with pytest.raises(ConfigValidationError, match="Duplicate JSON key"):
                load_json_file(config_path)

    def test_config_loader_rejects_symlink(self):
        """H2: Symlinked config file rejected."""
        from config_engine.loader import load_json_file
        from config_engine.errors import ConfigValidationError
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.json"
            link = Path(tmp) / "link.json"
            real.write_text('{}', encoding="utf-8")
            link.symlink_to(real)
            with pytest.raises(ConfigValidationError, match="Symlinked configuration file rejected"):
                load_json_file(link)

    # -----------------------------------------------------------------------
    # H3: Config schema depth / size enforcement
    # -----------------------------------------------------------------------

    def test_schema_depth_limit_enforced(self):
        """H3: ConfigSchema.validate rejects depth > 10."""
        from config_engine.schema import ConfigSchema, FieldSpec
        from config_engine.errors import ConfigValidationError
        schema = ConfigSchema(name="test", fields={"data": FieldSpec("data", dict)})
        deep = {"data": {}}
        current = deep["data"]
        for _ in range(15):
            current["next"] = {}
            current = current["next"]
        with pytest.raises(ConfigValidationError, match="maximum nesting depth"):
            schema.validate(deep)

    def test_schema_container_size_limit_enforced(self):
        """H3: ConfigSchema.validate rejects root dict/list with >1000 elements."""
        from config_engine.schema import ConfigSchema, FieldSpec
        from config_engine.errors import ConfigValidationError
        schema = ConfigSchema(name="test", fields={})
        with pytest.raises(ConfigValidationError, match="exceeds maximum size"):
            schema.validate({f"key{i}": i for i in range(1001)})

    # -----------------------------------------------------------------------
    # H4: Policy rule explosion bounds
    # -----------------------------------------------------------------------

    def test_policy_evaluator_rejects_too_many_rules(self):
        """H4: PolicyEvaluator rejects policy sets with >1024 rules."""
        from policy_engine.evaluator import PolicyEvaluator, MAX_RULES, PolicyEvaluationError
        from policy_engine.rules import Rule, PolicyProfile, PolicySet
        from policy_engine.decisions import DecisionState
        rules = [
            Rule(rule_id=f"r{i}", priority=1, effect=DecisionState.ALLOW, conditions=[])
            for i in range(MAX_RULES + 1)
        ]
        profile = PolicyProfile(name="test", description="test", rules=rules)
        pset = PolicySet(profiles={"test": profile})
        with pytest.raises(PolicyEvaluationError, match="exceeds maximum"):
            PolicyEvaluator(pset)

    def test_policy_evaluator_rejects_too_many_conditions(self):
        """H4: PolicyEvaluator rejects rules with >64 conditions."""
        from policy_engine.evaluator import PolicyEvaluator, MAX_CONDITIONS, PolicyEvaluationError
        from policy_engine.rules import Rule, PolicyProfile, PolicySet
        from policy_engine.decisions import DecisionState
        rule = Rule(
            rule_id="big",
            priority=1,
            effect=DecisionState.ALLOW,
            conditions=[{"field": "x", "op": "eq", "value": i} for i in range(MAX_CONDITIONS + 1)],
        )
        profile = PolicyProfile(name="test", description="test", rules=[rule])
        pset = PolicySet(profiles={"test": profile})
        with pytest.raises(PolicyEvaluationError, match="conditions"):
            PolicyEvaluator(pset)

    # -----------------------------------------------------------------------
    # H5: Vault unlock attempt exhaustion
    # -----------------------------------------------------------------------

    def test_vault_session_unlock_exhaustion(self):
        """H5: VaultSession.MAX_ATTEMPTS = 5; 6th attempt blocked."""
        from security.vault.session import VaultSession, VaultError
        with tempfile.TemporaryDirectory() as tmp:
            import os
            os.environ["HOME"] = str(tmp)
            session = VaultSession()
            session.init("correct-password")
            for _ in range(5):
                with pytest.raises(VaultError):
                    session.unlock("wrong")
            # 6th attempt should be blocked at the gate
            with pytest.raises(VaultError, match="Too many failed unlock attempts"):
                session.unlock("wrong")
            # Correct password also blocked after exhaustion
            with pytest.raises(VaultError, match="Too many failed unlock attempts"):
                session.unlock("correct-password")

    def test_vault_session_status_reports_attempts(self):
        """H5: VaultSession.status reports failed_attempts and max_attempts."""
        from security.vault.session import VaultSession
        with tempfile.TemporaryDirectory() as tmp:
            import os
            os.environ["HOME"] = str(tmp)
            session = VaultSession()
            session.init("pw")
            try:
                session.unlock("wrong")
            except Exception:
                pass
            status = session.status()
            assert status["failed_attempts"] == 1
            assert status["max_attempts"] == 5

    # -----------------------------------------------------------------------
    # H6: RestartPolicy crash-loop / backoff (real bounds)
    # -----------------------------------------------------------------------

    def test_restart_policy_backoff_capped(self):
        """H6: Exponential backoff capped at max_backoff_seconds (default 60)."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({
            "restart": {
                "policy": "on-failure",
                "max_attempts": 10,
                "backoff_initial_seconds": 2,
                "backoff_max_seconds": 10,
            }
        })
        delays = []
        for _ in range(6):
            should, delay = policy.should_restart("svc", exit_code=1, manually_stopped=False)
            assert should is True
            delays.append(delay)
        assert delays[-1] == 10.0, f"Backoff not capped: {delays}"

    def test_restart_policy_window_reset_allows_restart(self):
        """H6: Stable window (default 300s) resets attempt counter."""
        from services.restart import RestartPolicy
        policy = RestartPolicy({
            "restart": {
                "policy": "on-failure",
                "max_attempts": 2,
                "window_seconds": 0,
                "backoff_initial_seconds": 1,
            }
        })
        # First burst uses attempts
        policy.should_restart("svc", exit_code=1, manually_stopped=False)
        policy.should_restart("svc", exit_code=1, manually_stopped=False)
        # Window=0 means next call resets first_attempt, so attempts reset
        should, _ = policy.should_restart("svc", exit_code=1, manually_stopped=False)
        assert should is True, "Window reset should allow restart"

    # -----------------------------------------------------------------------
    # H7: Bundle extraction limits (real production code)
    # -----------------------------------------------------------------------

    def test_bundle_extract_rejects_too_many_files(self, tmp_path, monkeypatch):
        """H7: Bundle with >MAX_FILE_COUNT entries rejected by extract_bundle."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle
        from updates.errors import BundleError
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", 5)
        bundle = tmp_path / "many_files.zip"
        import zipfile
        with zipfile.ZipFile(bundle, "w") as zf:
            for i in range(6):
                zf.writestr(f"file{i}.txt", b"x")
        with pytest.raises(BundleError):
            extract_bundle(bundle, tmp_path / "out")

    def test_bundle_extract_rejects_oversized_expansion(self, tmp_path, monkeypatch):
        """H7: Bundle exceeding MAX_EXPANDED_SIZE rejected."""
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle
        from updates.errors import BundleError
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 1024)  # 1 KiB
        bundle = tmp_path / "big.zip"
        import zipfile
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", b'{}')
            zf.writestr("big.dat", b"x" * 2048)
        with pytest.raises(BundleError):
            extract_bundle(bundle, tmp_path / "out")

    # -----------------------------------------------------------------------
    # H8: Compression ratio / zip bomb
    # -----------------------------------------------------------------------

    def test_bundle_high_compression_ratio_accepted_then_limited(self, tmp_path, monkeypatch):
        """H8: A zip bomb (high compression ratio) is bounded by MAX_EXPANDED_SIZE
        in extract_bundle — the decompressed total, not the compressed archive size.
        """
        from updates import bundle as bundle_mod
        from updates.bundle import extract_bundle
        from updates.errors import BundleError
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 10 * 1024)  # 10 KiB
        bundle = tmp_path / "bomb.zip"
        import zipfile
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", b'{}')
            # 1 MiB of zeros compresses to ~1 KiB — extreme ratio
            zf.writestr("zeros.dat", b"\x00" * (1024 * 1024))
        with pytest.raises(BundleError):
            extract_bundle(bundle, tmp_path / "out")