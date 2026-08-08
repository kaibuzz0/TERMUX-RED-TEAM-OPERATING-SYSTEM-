"""Milestone 19 — Boundedness: verify every production bound is enforced.

Production bounds catalog:
- H1: derive_key() — n power-of-two, n≥2, salt≥16, memory ≤1 GiB (already in resource_exhaustion)
- H2: load_json_file() — 5 MB max_size, symlinks rejected (already in resource_exhaustion)
- H3: ConfigSchema — depth>10, container>1000 (already in resource_exhaustion)
- H4: PolicyEvaluator — MAX_RULES=1024, MAX_CONDITIONS=64 (already in resource_exhaustion)
- H5: VaultSession — MAX_ATTEMPTS=5 (already in resource_exhaustion)
- H6: RestartPolicy — backoff capped, window reset (already in resource_exhaustion)
- H7: Bundle extract — MAX_FILE_COUNT, MAX_EXPANDED_SIZE (already in resource_exhaustion)
- H8: Zip bomb — bounded by MAX_EXPANDED_SIZE (already in resource_exhaustion)
- **NEW below:** check_bounded_size, validate_id, FieldSpec length, BrokerSession history, PolicyRequest schema.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


class TestPolicySchemaBoundedness:
    """B1: policy_engine.schema bounds — check_bounded_size, validate_id, FieldSpec."""

    def test_check_bounded_size_max_depth_8(self):
        """B1: check_bounded_size rejects depth > 8."""
        from policy_engine.schema import check_bounded_size, PolicyValidationError
        deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": 1}}}}}}}}}
        with pytest.raises(PolicyValidationError, match="maximum nesting depth"):
            check_bounded_size(deep, max_depth=8)

    def test_check_bounded_size_depth_8_ok(self):
        """B1: check_bounded_size accepts depth == 8."""
        from policy_engine.schema import check_bounded_size
        obj: dict | int = 1
        for _ in range(8):
            obj = {"k": obj}
        check_bounded_size(obj, max_depth=8)  # should not raise

    def test_check_bounded_size_max_size_1000(self):
        """B1: check_bounded_size rejects dict/list with >1000 items."""
        from policy_engine.schema import check_bounded_size, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="exceeds maximum size"):
            check_bounded_size({f"k{i}": i for i in range(1001)}, max_size=1000)

    def test_check_bounded_size_max_size_list(self):
        """B1: check_bounded_size rejects list with >1000 items."""
        from policy_engine.schema import check_bounded_size, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="exceeds maximum size"):
            check_bounded_size([i for i in range(1001)], max_size=1000)

    def test_check_bounded_size_max_leaf_4096(self):
        """B1: check_bounded_size rejects string >4096 chars."""
        from policy_engine.schema import check_bounded_size, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="maximum length"):
            check_bounded_size("x" * 4097, max_leaf_len=4096)

    def test_validate_id_empty_rejected(self):
        """B1: validate_id rejects empty string."""
        from policy_engine.schema import validate_id, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="must not be empty"):
            validate_id("")

    def test_validate_id_too_long_rejected(self):
        """B1: validate_id rejects >64 chars."""
        from policy_engine.schema import validate_id, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="too long"):
            validate_id("a" * 65)

    def test_validate_id_non_alpha_start_rejected(self):
        """B1: validate_id rejects identifiers not starting with a letter."""
        from policy_engine.schema import validate_id, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="must start with a letter"):
            validate_id("1invalid")

    def test_validate_id_invalid_chars_rejected(self):
        """B1: validate_id rejects invalid characters."""
        from policy_engine.schema import validate_id, PolicyValidationError
        with pytest.raises(PolicyValidationError, match="invalid characters"):
            validate_id("bad!id")

    def test_validate_id_exactly_64_ok(self):
        """B1: validate_id accepts exactly 64 alphanumeric chars."""
        from policy_engine.schema import validate_id
        valid = "a" + "b" * 63
        assert len(valid) == 64
        assert validate_id(valid) == valid

    def test_field_spec_max_length_enforced(self):
        """B1: TypedSchema validates FieldSpec.max_length."""
        from policy_engine.schema import TypedSchema, FieldSpec, PolicyValidationError
        schema = TypedSchema("test", 1, {"name": FieldSpec("name", str, max_length=10)})
        with pytest.raises(PolicyValidationError, match="too long"):
            schema.validate({"name": "x" * 11})

    def test_field_spec_min_length_enforced(self):
        """B1: TypedSchema validates FieldSpec.min_length."""
        from policy_engine.schema import TypedSchema, FieldSpec, PolicyValidationError
        schema = TypedSchema("test", 1, {"name": FieldSpec("name", str, min_length=3)})
        with pytest.raises(PolicyValidationError, match="too short"):
            schema.validate({"name": "ab"})


class TestPolicyRequestBoundedness:
    """B2: PolicyRequest construction invokes check_bounded_size."""

    def test_policy_request_rejects_oversized_context(self):
        """B2: PolicyRequest.from_dict rejects context dict >1000 keys."""
        from policy_engine.requests import PolicyRequest
        from policy_engine.errors import PolicyValidationError
        with pytest.raises(PolicyValidationError, match="exceeds maximum size"):
            PolicyRequest.from_dict({
                "schema_version": 1,
                "request_id": "r1",
                "actor": {"type": "operator", "id": "u1"},
                "capability": "service.list",
                "resource": {"type": "service", "id": "svc1"},
                "context": {f"k{i}": i for i in range(1001)},
            })

    def test_policy_request_rejects_deeply_nested_context(self):
        """B2: PolicyRequest.from_dict rejects context depth >8."""
        from policy_engine.requests import PolicyRequest
        from policy_engine.errors import PolicyValidationError
        deep_ctx: dict | int = 1
        for _ in range(15):
            deep_ctx = {"next": deep_ctx}
        with pytest.raises(PolicyValidationError, match="maximum nesting depth"):
            PolicyRequest.from_dict({
                "schema_version": 1,
                "request_id": "r1",
                "actor": {"type": "operator", "id": "u1"},
                "capability": "service.list",
                "resource": {"type": "service", "id": "svc1"},
                "context": deep_ctx,
            })

    def test_policy_request_rejects_long_leaf_string(self):
        """B2: PolicyRequest.from_dict rejects leaf string >4096 chars."""
        from policy_engine.requests import PolicyRequest
        from policy_engine.errors import PolicyValidationError
        with pytest.raises(PolicyValidationError, match="maximum length"):
            PolicyRequest.from_dict({
                "schema_version": 1,
                "request_id": "r1",
                "actor": {"type": "operator", "id": "u1"},
                "capability": "service.list",
                "resource": {"type": "service", "id": "svc1"},
                "context": {"note": "x" * 4097},
            })

    def test_policy_request_accepts_bounded_context(self):
        """B2: PolicyRequest.from_dict accepts context within bounds."""
        from policy_engine.requests import PolicyRequest
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "r1",
            "actor": {"type": "operator", "id": "u1"},
            "capability": "service.list",
            "resource": {"type": "service", "id": "svc1"},
            "context": {"k" + str(i): i for i in range(1000)},
        })
        assert req.request_id == "r1"


class TestBrokerSessionBoundedness:
    """B3: BrokerSession history pruned at -100 entries on persist."""

    def test_session_persist_truncates_history_to_100(self):
        """B3: _persist keeps only last 100 history entries."""
        from hive_broker.session import BrokerSession
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            session = BrokerSession(state_root=state)
            for i in range(150):
                session.history.append({"idx": i, "action": "noop"})
            session._persist()
            data = json.loads((state / f"{session.session_id}.json").read_text())
            assert len(data["history"]) == 100
            assert data["history"][0]["idx"] == 50
            assert data["history"][-1]["idx"] == 149

    def test_session_persist_keeps_all_if_under_100(self):
        """B3: _persist keeps all entries when <=100."""
        from hive_broker.session import BrokerSession
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            session = BrokerSession(state_root=state)
            for i in range(42):
                session.history.append({"idx": i})
            session._persist()
            data = json.loads((state / f"{session.session_id}.json").read_text())
            assert len(data["history"]) == 42


class TestProfileResolverBoundedness:
    """B4: ProfileResolver inheritance depth bound (MAX_DEPTH=8)."""

    def test_profile_resolver_depth_9_rejected(self):
        """B4: Inheritance chain depth >8 raises ConfigProfileError."""
        from config_engine.profiles import ProfileResolver, ConfigProfileError
        profiles: dict[str, dict[str, str]] = {}
        for i in range(9):
            profiles[f"p{i}"] = {"_parent": f"p{i+1}"}
        resolver = ProfileResolver(user_profiles=profiles)
        with pytest.raises(ConfigProfileError, match="exceeds maximum"):
            resolver.resolve("p0")

    def test_profile_resolver_depth_8_accepted(self):
        """B4: Inheritance chain depth == 8 accepted."""
        from config_engine.profiles import ProfileResolver, ConfigProfileError
        profiles: dict[str, dict[str, str]] = {}
        for i in range(8):
            profiles[f"p{i}"] = {"_parent": f"p{i+1}"}
        profiles["p8"] = {"value": "ok"}
        resolver = ProfileResolver(user_profiles=profiles)
        result = resolver.resolve("p0")
        assert result["value"] == "ok"


class TestConfigHistoryBoundedness:
    """B5: ConfigurationStore history has no auto-prune; verify counter grows."""

    def test_config_store_history_counter_grows_without_limit(self):
        """B5: archive() does not cap history count; files grow indefinitely.

        This is an *accepted debt* (Milestone 18 Item #1). The test documents
        the current behavior so a future Milestone can implement rotation.
        """
        from config_engine.persistence import ConfigurationStore
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigurationStore(
                config_root=Path(tmp) / "config",
                state_root=Path(tmp) / "state",
            )
            store.ensure_dirs()
            for i in range(5):
                store.archive_transaction(
                    new={"_meta": {"version": i}, "data": i},
                    previous=None,
                    profile="default",
                    author="test",
                    validation_result="ok",
                    migration_performed=False,
                )
            records = list(store.history_dir.glob("*.record.json"))
            assert len(records) == 5
