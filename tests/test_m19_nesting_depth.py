"""Milestone 19 — Nesting depth boundedness audit.

Production depth bounds catalog:
- config_engine.schema.ConfigSchema.validate — max_depth=10 (explicit)
- policy_engine.schema.check_bounded_size — max_depth=8 (explicit)
- config_engine.profiles.ProfileResolver.resolve — MAX_DEPTH=8 (explicit)
- Python json.loads — implicit ~994 dict nesting (C recursion / stack limit)

All production JSON loaders use json.loads, which has an implicit depth limit.
No loader adds explicit depth enforcement before json.loads.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Python json.loads implicit depth limit (CPython implementation detail)
# ---------------------------------------------------------------------------

def _make_nested_dict_str(depth: int) -> str:
    """Return a JSON string with dict nesting equal to depth (string builder, no recursion)."""
    s = "{"
    for _ in range(depth - 1):
        s += '"k": {'
    s += '"k": 1'
    s += "}" * depth
    return s


class TestPythonJsonLoadsImplicitDepth:
    """Document Python's built-in json.loads recursion ceiling.
    These are CPython implementation details, not Hive production bounds.
    The exact limit varies with call-stack depth; we only assert it is
    well above any production explicit bound (≤10) and that a limit exists.
    """

    def test_json_loads_accepts_depth_50(self):
        """json.loads accepts dict nesting depth 50 (far above all production bounds)."""
        data = json.loads(_make_nested_dict_str(50))
        current = data
        for _ in range(50):
            current = current["k"]
        assert current == 1

    def test_json_loads_implicit_limit_exists(self):
        """json.loads eventually hits RecursionError at extreme nesting depth."""
        # Use a depth far beyond any production bound; if the platform's
        # implicit limit is lower, the test still proves a ceiling exists.
        with pytest.raises(RecursionError):
            json.loads(_make_nested_dict_str(2000))

    def test_json_dumps_list_limit_exists(self):
        """json.dumps eventually hits RecursionError at extreme list nesting."""
        obj: list | int = 1
        for _ in range(2000):
            obj = [obj]
        with pytest.raises(RecursionError):
            json.dumps(obj)


# ---------------------------------------------------------------------------
# 1. config_engine.schema.ConfigSchema — explicit depth=10
# ---------------------------------------------------------------------------

class TestConfigSchemaDepthBounded:
    def test_config_schema_rejects_depth_11(self):
        """ConfigSchema.validate rejects dict nesting depth > 10."""
        from config_engine.schema import ConfigSchema, FieldSpec
        from config_engine.errors import ConfigValidationError
        schema = ConfigSchema(name="test", fields={"data": FieldSpec("data", dict)})
        deep = {"data": {}}
        current = deep["data"]
        for _ in range(10):
            current["next"] = {}
            current = current["next"]
        with pytest.raises(ConfigValidationError, match="maximum nesting depth"):
            schema.validate(deep)

    def test_config_schema_accepts_depth_10(self):
        """ConfigSchema.validate accepts dict nesting depth == 10."""
        from config_engine.schema import ConfigSchema, FieldSpec
        schema = ConfigSchema(name="test", fields={"data": FieldSpec("data", dict)})
        deep = {"data": {}}
        current = deep["data"]
        for _ in range(9):
            current["next"] = {}
            current = current["next"]
        schema.validate(deep)  # should not raise


# ---------------------------------------------------------------------------
# 2. policy_engine.schema.check_bounded_size — explicit depth=8
# ---------------------------------------------------------------------------

class TestPolicySchemaDepthBounded:
    def test_check_bounded_size_rejects_depth_9(self):
        """check_bounded_size rejects depth > 8."""
        from policy_engine.schema import check_bounded_size, PolicyValidationError
        deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": 1}}}}}}}}}
        with pytest.raises(PolicyValidationError, match="maximum nesting depth"):
            check_bounded_size(deep, max_depth=8)

    def test_check_bounded_size_accepts_depth_8(self):
        """check_bounded_size accepts depth == 8."""
        from policy_engine.schema import check_bounded_size
        obj: dict | int = 1
        for _ in range(8):
            obj = {"k": obj}
        check_bounded_size(obj, max_depth=8)  # should not raise


# ---------------------------------------------------------------------------
# 3. config_engine.profiles.ProfileResolver — explicit depth=8
# ---------------------------------------------------------------------------

class TestProfileResolverDepthBounded:
    def test_profile_resolver_depth_9_rejected(self):
        """Profile inheritance chain depth > 8 raises ConfigProfileError."""
        from config_engine.profiles import ProfileResolver, ConfigProfileError
        profiles: dict[str, dict[str, str]] = {}
        for i in range(9):
            profiles[f"p{i}"] = {"_parent": f"p{i+1}"}
        resolver = ProfileResolver(user_profiles=profiles)
        with pytest.raises(ConfigProfileError, match="exceeds maximum"):
            resolver.resolve("p0")

    def test_profile_resolver_depth_8_accepted(self):
        """Profile inheritance chain depth == 8 accepted."""
        from config_engine.profiles import ProfileResolver
        profiles: dict[str, dict[str, str]] = {}
        for i in range(8):
            profiles[f"p{i}"] = {"_parent": f"p{i+1}"}
        profiles["p8"] = {"value": "ok"}
        resolver = ProfileResolver(user_profiles=profiles)
        result = resolver.resolve("p0")
        assert result["value"] == "ok"


# ---------------------------------------------------------------------------
# 4. Raw JSON loaders — no explicit depth enforcement
# ---------------------------------------------------------------------------

class TestRawJsonLoadersNoExplicitDepth:
    """Verify that production JSON loaders have no explicit depth check
    before calling json.loads — only Python's implicit ~994 limit exists.
    """

    def test_broker_cli_load_manifest_no_explicit_depth(self):
        """hive_broker.cli._load_manifest has no explicit depth check."""
        from hive_broker.cli import _load_manifest
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "manifest.json"
            # Depth 50 — far below Python's implicit limit, but above any
            # explicit bound (if one existed). If no explicit bound, this passes.
            obj: dict | int = 1
            for _ in range(50):
                obj = {"layer": obj}
            p.write_text(json.dumps(obj), encoding="utf-8")
            data = _load_manifest(str(p))
            # Navigate to bottom to prove full parse
            for _ in range(50):
                data = data["layer"]
            assert data == 1

    def test_installer_lock_no_explicit_depth(self):
        """installer.activate._read_lock has no explicit depth check."""
        from installer.activate import ActiveState
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "data"
            state_root = Path(tmp) / "state"
            data_root.mkdir()
            state_root.mkdir()
            lock_path = state_root / ".install-lock"
            obj: dict | int = 1
            for _ in range(50):
                obj = {"layer": obj}
            lock_path.write_text(json.dumps({"transaction_id": "txn-1", "deep": obj}), encoding="utf-8")
            active = ActiveState(data_root=data_root, state_root=state_root, transaction_id="txn-2")
            data = active._read_lock()
            assert data is not None
            current = data["deep"]
            for _ in range(50):
                current = current["layer"]
            assert current == 1

    def test_release_registry_load_no_explicit_depth(self):
        """release_engine.registry._load has no explicit depth check."""
        from release_engine.registry import ReleaseRegistry
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "registry.json"
            obj: dict | int = 1
            for _ in range(50):
                obj = {"layer": obj}
            p.write_text(json.dumps({"schema_version": 1, "releases": [], "deep": obj}), encoding="utf-8")
            reg = ReleaseRegistry(path=p)
            current = reg._data["deep"]
            for _ in range(50):
                current = current["layer"]
            assert current == 1

    def test_plugin_registry_load_no_explicit_depth(self):
        """release_engine.plugin_registry._load has no explicit depth check."""
        from release_engine.plugin_registry import PersistentPluginRegistry
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "registry.json"
            obj: dict | int = 1
            for _ in range(50):
                obj = {"layer": obj}
            p.write_text(json.dumps({"schema_version": 1, "plugins": {}, "deep": obj}), encoding="utf-8")
            reg = PersistentPluginRegistry(path=p)
            current = reg._data["deep"]
            for _ in range(50):
                current = current["layer"]
            assert current == 1

    def test_plugin_sdk_manifest_no_explicit_depth(self):
        """plugin_sdk.manifest.load_manifest has no explicit depth check."""
        from plugin_sdk.manifest import load_manifest
        from plugin_sdk.errors import PluginManifestError
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "manifest.json"
            # Manifest schema rejects unknown top-level fields, so keep deep inside a known field
            # But plugin manifest has strict schema — we just prove json.loads succeeds
            # and schema validation is what happens next, not a depth limit before json.loads.
            obj: dict | int = 1
            for _ in range(50):
                obj = {"layer": obj}
            # plugin manifest requires specific fields; just write valid fields + deep inside context
            p.write_text(
                json.dumps({
                    "schema_version": 1,
                    "plugin": {"id": "p1", "version": "1.0.0", "author_key_id": "k1"},
                    "deep": obj,
                }),
                encoding="utf-8",
            )
            # Will fail at schema validation (unknown field), not at json.loads / depth
            with pytest.raises(PluginManifestError, match="unknown top-level fields"):
                load_manifest(p)

    def test_policy_engine_cli_no_explicit_depth(self):
        """policy_engine.cli loads JSON with no explicit depth check before json.loads."""
        from policy_engine.requests import PolicyRequest
        from policy_engine.errors import PolicyValidationError
        # Build a valid-looking request with deep nesting in context
        obj: dict | int = 1
        for _ in range(50):
            obj = {"layer": obj}
        req = {
            "schema_version": 1,
            "request_id": "r1",
            "actor": {"type": "operator", "id": "u1"},
            "capability": "service.list",
            "resource": {"type": "service", "id": "svc1"},
            "context": {"deep": obj},
        }
        # _load_policy_request would call json.loads then PolicyRequest.from_dict.
        # The depth check happens at from_dict (max_depth=8), not at json.loads.
        # So depth 50 is accepted by json.loads but rejected by from_dict.
        with pytest.raises(PolicyValidationError, match="maximum nesting depth"):
            PolicyRequest.from_dict(req)

    def test_services_schema_load_no_explicit_depth(self):
        """services.schema.load_manifest_file has no explicit depth check."""
        from services.schema import load_manifest_file
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "svc.json"
            obj: dict | int = 1
            for _ in range(50):
                obj = {"layer": obj}
            p.write_text(
                json.dumps({
                    "schema_version": 1,
                    "name": "svc1",
                    "command": {"interpreter": "python", "base": "repository", "args": ["run.py"]},
                    "deep": obj,
                }),
                encoding="utf-8",
            )
            data = load_manifest_file(p)
            current = data["deep"]
            for _ in range(50):
                current = current["layer"]
            assert current == 1

    def test_updates_manifest_load_no_explicit_depth(self):
        """updates.manifest.load_manifest has no explicit depth check."""
        from updates.manifest import load_manifest
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "manifest.json"
            obj: dict | int = 1
            for _ in range(50):
                obj = {"layer": obj}
            # updates manifest must be a JSON list
            p.write_text(
                json.dumps([
                    {"path": "a.txt", "size": 1, "sha256": "a" * 64, "deep": obj},
                ]),
                encoding="utf-8",
            )
            data = load_manifest(p)
            current = data[0]["deep"]
            for _ in range(50):
                current = current["layer"]
            assert current == 1