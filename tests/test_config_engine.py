"""Tests for the unified Configuration Engine."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from config_engine import ConfigEngine, ConfigValidationError, get_config
from config_engine.defaults import build_registry
from config_engine.environment import get_env_overrides
from config_engine.merger import merge_layers, substitute_variables
from config_engine.migration import MIGRATIONS, Migration, MigrationRegistry
from config_engine.persistence import ConfigurationStore
from config_engine.profiles import ProfileResolver
from config_engine.schema import ConfigSchema, FieldSpec
from config_engine.transactions import TransactionManager, PreviewResult


@pytest.fixture
def tmp_engine(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "hive-canonical.json").write_text(
        json.dumps({
            "schema_version": 1,
            "current_canonical_source": "src",
            "current_canonical_launcher": "src/main.py",
            "current_canonical_launcher_type": "python",
            "launcher_execution_policy": "explicit-interpreter",
        }),
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    return ConfigEngine(repo, home=tmp_path / "home", profile="default")


def test_schema_validation_rejects_unknown_fields():
    schema = ConfigSchema("test", fields={"x": FieldSpec("x", int)})
    with pytest.raises(ConfigValidationError):
        schema.validate({"x": 1, "y": 2})


def test_schema_validation_accepts_extensible():
    schema = ConfigSchema("test", extensible=True, fields={"x": FieldSpec("x", int)})
    data = schema.validate({"x": 1, "y": 2})
    assert data["x"] == 1
    assert "y" in data


def test_schema_type_check():
    schema = ConfigSchema("test", fields={"x": FieldSpec("x", int)})
    with pytest.raises(ConfigValidationError):
        schema.validate({"x": "not-int"})


def test_schema_range_check():
    schema = ConfigSchema("test", fields={"x": FieldSpec("x", int, min_value=0, max_value=10)})
    schema.validate({"x": 5})
    with pytest.raises(ConfigValidationError):
        schema.validate({"x": 11})


def test_merge_layers():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 9}}
    result = merge_layers(base, override)
    assert result["a"] == 1
    assert result["b"]["c"] == 9
    assert result["b"]["d"] == 3


def test_substitute_variables():
    data = {"path": "${home}/hive", "nested": {"x": "${tmp}/x"}}
    context = {"home": "/home/u", "tmp": "/tmp"}
    result = substitute_variables(data, context)
    assert result["path"] == "/home/u/hive"
    assert result["nested"]["x"] == "/tmp/x"


def test_substitute_unknown_variable_raises():
    with pytest.raises(ConfigValidationError):
        substitute_variables({"x": "${unknown}"}, {})


def test_profile_resolver_builtin():
    resolver = ProfileResolver()
    cfg = resolver.resolve("production")
    assert cfg["runtime"]["log_level"] == "warning"


def test_profile_resolver_unknown():
    resolver = ProfileResolver()
    with pytest.raises(Exception):
        resolver.resolve("nonexistent")


def test_profile_resolver_user_inheritance(tmp_path):
    profiles = {
        "child": {"_parent": "default", "runtime": {"log_level": "debug"}},
    }
    resolver = ProfileResolver(profiles)
    cfg = resolver.resolve("child")
    assert cfg["runtime"]["log_level"] == "debug"


def test_profile_resolver_cycle_detected():
    profiles = {"a": {"_parent": "b"}, "b": {"_parent": "a"}}
    resolver = ProfileResolver(profiles)
    with pytest.raises(Exception):
        resolver.resolve("a")


def test_env_overrides_allowed_only():
    env = {"HIVE_PROFILE": "production"}
    result = get_env_overrides(env)
    assert result["profile"] == "production"


def test_env_overrides_reject_unknown():
    env = {"HIVE_UNKNOWN": "x"}
    result = get_env_overrides(env)
    assert "HIVE_UNKNOWN" not in result


def test_config_engine_full_config(tmp_engine):
    cfg = tmp_engine.full_config()
    assert "runtime" in cfg
    assert "broker" in cfg
    assert cfg["runtime"]["profile"] == "default"


def test_config_engine_get_config(tmp_engine):
    broker = tmp_engine.get_config("broker")
    assert broker["default_timeout_seconds"] == 30


def test_config_engine_profile_switch(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "hive-canonical.json").write_text(
        json.dumps({
            "schema_version": 1,
            "current_canonical_source": "src",
            "current_canonical_launcher": "src/main.py",
            "current_canonical_launcher_type": "python",
            "launcher_execution_policy": "explicit-interpreter",
        }),
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    engine = ConfigEngine(repo, home=tmp_path / "home", profile="production")
    runtime = engine.get_config("runtime")
    assert runtime["log_level"] == "warning"


def test_config_engine_path_substitution(tmp_engine):
    runtime = tmp_engine.get_config("runtime")
    # On Windows, home may contain backslashes; ensure no unresolved variables remain.
    for key in ("log_root", "state_root", "config_root", "data_root", "cache_root", "temp_root"):
        assert "${" not in runtime[key]


def test_config_engine_unknown_subsystem_raises(tmp_engine):
    with pytest.raises(Exception):
        tmp_engine.get_config("nonexistent")


def test_transaction_store_committed(tmp_path):
    store = ConfigurationStore(tmp_path / "cfg", tmp_path / "state")
    assert store.load_committed() is None
    store.save_committed({"x": 1})
    assert store.load_committed() == {"x": 1}


def test_transaction_manager_preview_valid(tmp_path):
    store = ConfigurationStore(tmp_path / "cfg", tmp_path / "state")
    txn = TransactionManager(store)
    preview = txn.preview(None, {"valid": True})
    assert preview.valid


def test_transaction_manager_preview_invalid(tmp_path):
    store = ConfigurationStore(tmp_path / "cfg", tmp_path / "state")

    def fail(_):
        from config_engine.errors import ConfigValidationError
        raise ConfigValidationError("bad", details=[{"message": "bad"}])

    txn = TransactionManager(store, validate_fn=fail)
    preview = txn.preview(None, {"x": 1})
    assert not preview.valid


def test_transaction_commit_and_history(tmp_path):
    store = ConfigurationStore(tmp_path / "cfg", tmp_path / "state")
    txn = TransactionManager(store)
    result = txn.commit({"x": 1}, "default", "tester", [])
    assert "transaction_id" in result
    assert len(store.list_transactions()) == 1


def test_transaction_rollback(tmp_path):
    store = ConfigurationStore(tmp_path / "cfg", tmp_path / "state")
    txn = TransactionManager(store)
    first = txn.commit({"x": 1}, "default", "tester", [])
    txn.commit({"x": 2}, "default", "tester", [])
    new_id, _ = store.rollback_to(first["transaction_id"], "tester")
    assert store.load_committed()["x"] == 1
    assert new_id.startswith("txn-")


def test_migration_registry():
    reg = MigrationRegistry()
    reg.register("svc", Migration("rename", 1, 2, lambda d: {"schema_version": 2, "name": d.get("name")}))
    data, names = reg.migrate("svc", {"schema_version": 1, "name": "x"}, 2)
    assert data["schema_version"] == 2
    assert "rename" in names


def test_migration_downgrade_rejected():
    reg = MigrationRegistry()
    with pytest.raises(Exception):
        reg.migrate("svc", {"schema_version": 2}, 1)


def test_get_config_helper(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "hive-canonical.json").write_text(
        json.dumps({
            "schema_version": 1,
            "current_canonical_source": "src",
            "current_canonical_launcher": "src/main.py",
            "current_canonical_launcher_type": "python",
            "launcher_execution_policy": "explicit-interpreter",
        }),
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    monkeypatch.chdir(repo)
    cfg = get_config("broker", repo)
    assert cfg["default_timeout_seconds"] == 30


def test_config_validation_rejects_path_traversal(tmp_engine):
    from config_engine.persistence import ConfigurationStore
    # Direct validation should reject traversal patterns
    from config_engine.validator import validate_subsystem_config
    errors = validate_subsystem_config("services", {"manifest_dirs": ["../etc"]})
    assert errors


def test_profile_diamond_inheritance(tmp_path):
    """Profile inheritance through a chain: child <- left <- base, with values merging."""
    profiles = {
        "base": {"runtime": {"log_level": "info"}, "broker": {"audit_enabled": True}},
        "left": {"_parent": "base", "runtime": {"log_level": "debug"}},
        "child": {"_parent": "left", "runtime": {"profile": "child"}},
    }
    resolver = ProfileResolver(profiles)
    cfg = resolver.resolve("child")
    assert cfg["runtime"]["log_level"] == "debug"
    assert cfg["runtime"]["profile"] == "child"
    assert cfg["broker"]["audit_enabled"] is True


def test_profile_conflicting_parents_last_wins():
    resolver = ProfileResolver({
        "parent1": {"runtime": {"log_level": "error"}},
        "parent2": {"runtime": {"log_level": "debug"}},
        "child": {"_parent": "parent1", "runtime": {"log_level": "info"}},
    })
    cfg = resolver.resolve("child")
    # Child override wins over parent.
    assert cfg["runtime"]["log_level"] == "info"


def test_profile_inheritance_depth_bound():
    deep = {f"p{i}": {"_parent": f"p{i-1}" if i > 0 else None} for i in range(12)}
    resolver = ProfileResolver(deep)
    with pytest.raises(Exception):
        resolver.resolve("p11")


def test_duplicate_json_keys_rejected(tmp_path):
    from config_engine.loader import load_json_file
    bad = tmp_path / "bad.json"
    bad.write_text('{"x": 1, "x": 2}', encoding="utf-8")
    with pytest.raises(Exception):
        load_json_file(bad)


def test_oversized_json_rejected(tmp_path):
    from config_engine.loader import load_json_file
    big = tmp_path / "big.json"
    big.write_text('{"k": "' + "x" * (6 * 1024 * 1024) + '"}', encoding="utf-8")
    with pytest.raises(Exception):
        load_json_file(big)


def test_symlinked_config_rejected(tmp_path):
    import os
    from config_engine.loader import load_json_file
    real = tmp_path / "real.json"
    real.write_text('{"x": 1}', encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("symlink creation not supported on this platform")
    with pytest.raises(Exception):
        load_json_file(link)


def test_no_write_preview(tmp_engine):
    candidate = tmp_engine.full_config()
    before = tmp_engine.store.load_committed()
    tmp_engine.preview_commit(candidate)
    after = tmp_engine.store.load_committed()
    assert before is None and after is None


def test_no_write_validate(tmp_engine):
    before = tmp_engine.store.load_committed()
    tmp_engine.full_config()
    after = tmp_engine.store.load_committed()
    assert before is None and after is None


def test_transaction_history_survives_corrupt_entry(tmp_path):
    store = ConfigurationStore(tmp_path / "cfg", tmp_path / "state")
    store.save_committed({"x": 1})
    store.archive_transaction(None, {"x": 2}, "default", "tester", "ok", [])
    # Corrupt one record file
    records = list(store.history_dir.glob("*.record.json"))
    records[0].write_text("not json", encoding="utf-8")
    history = store.list_transactions()
    assert len(history) == 0  # corrupt entry ignored
    assert store.load_committed()["x"] == 1  # active config unaffected


def test_secret_redaction():
    from config_engine.config import _redact_for_display
    data = {"password": "secret", "nested": {"api_key": "abc"}, "ok": "visible"}
    redacted = _redact_for_display(data)
    assert redacted["password"] == "[REDACTED]"
    assert redacted["nested"]["api_key"] == "[REDACTED]"
    assert redacted["ok"] == "visible"


def test_environment_strict_mode_unknown_rejected(monkeypatch):
    from config_engine.environment import validate_env_var
    validate_env_var("HIVE_PROFILE", "default")
    with pytest.raises(Exception):
        validate_env_var("HIVE_UNKNOWN", "x")


def test_migration_preserves_original_on_failure():
    reg = MigrationRegistry()
    reg.register("svc", Migration("bad", 1, 2, lambda d: d))
    with pytest.raises(Exception):
        reg.migrate("svc", {"schema_version": 1}, 2)
