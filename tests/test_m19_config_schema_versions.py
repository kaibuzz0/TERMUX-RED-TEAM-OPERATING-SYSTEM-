"""Milestone 19 — Config schema versions inventory.

Verifies that all ConfigSchema registrations in config_engine.defaults and all
built-in profiles embed schema_version == 1 consistently.
"""

from __future__ import annotations

import pytest


class TestConfigSchemaRegistryVersions:
    def test_all_registered_schemas_are_version_1(self):
        """Every ConfigSchema in build_registry() has version == 1."""
        from config_engine.defaults import build_registry
        registry = build_registry()
        for name in registry._schemas:
            schema = registry.get(name)
            assert schema.version == 1, f"Schema {name!r} has version {schema.version}, expected 1"

    def test_all_schema_version_fieldspec_defaults_to_1(self):
        """Every registered schema defines schema_version FieldSpec with default=1 and required=True."""
        from config_engine.defaults import build_registry
        registry = build_registry()
        for name in registry._schemas:
            schema = registry.get(name)
            fs = schema.fields.get("schema_version")
            assert fs is not None, f"Schema {name!r} missing schema_version FieldSpec"
            assert fs.default == 1, f"Schema {name!r} schema_version default={fs.default}"
            assert fs.required is True, f"Schema {name!r} schema_version required={fs.required}"

    def test_runtime_schema_has_expected_fields(self):
        """Runtime schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("runtime")
        assert schema.name == "runtime"
        assert schema.version == 1
        assert "profile" in schema.fields
        assert "log_level" in schema.fields
        assert "max_log_size_mb" in schema.fields
        assert "max_log_count" in schema.fields

    def test_broker_schema_has_expected_fields(self):
        """Broker schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("broker")
        assert schema.name == "broker"
        assert schema.version == 1
        assert "max_active_transactions" in schema.fields
        assert "audit_enabled" in schema.fields
        assert "mutating_actions_enabled" in schema.fields

    def test_services_schema_has_expected_fields(self):
        """Services schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("services")
        assert schema.name == "services"
        assert schema.version == 1
        assert "max_failed_restarts" in schema.fields
        assert "backoff_base_seconds" in schema.fields
        assert "backoff_max_seconds" in schema.fields

    def test_vault_schema_has_expected_fields(self):
        """Vault schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("vault")
        assert schema.name == "vault"
        assert schema.version == 1
        assert "max_unlock_attempts" in schema.fields
        assert "key_derivation" in schema.fields
        assert "auto_lock_seconds" in schema.fields

    def test_updates_schema_has_expected_fields(self):
        """Updates schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("updates")
        assert schema.name == "updates"
        assert schema.version == 1
        assert "max_bundle_size_mb" in schema.fields
        assert "signature_required" in schema.fields
        assert "anti_rollback" in schema.fields

    def test_recovery_schema_has_expected_fields(self):
        """Recovery schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("recovery")
        assert schema.name == "recovery"
        assert schema.version == 1
        assert "max_journal_entries" in schema.fields
        assert "max_snapshots" in schema.fields
        assert "auto_snapshot" in schema.fields

    def test_operations_center_schema_has_expected_fields(self):
        """Operations Center schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("operations_center")
        assert schema.name == "operations_center"
        assert schema.version == 1
        assert "max_source_workers" in schema.fields
        assert "redact_secrets" in schema.fields

    def test_plugins_schema_has_expected_fields(self):
        """Plugins schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("plugins")
        assert schema.name == "plugins"
        assert schema.version == 1
        assert "sandbox" in schema.fields
        assert "max_plugin_memory_mb" in schema.fields

    def test_policy_schema_has_expected_fields(self):
        """Policy schema fields are present and version-locked."""
        from config_engine.defaults import build_registry
        schema = build_registry().get("policy")
        assert schema.name == "policy"
        assert schema.version == 1
        assert "active_profile" in schema.fields
        assert "strict_mode" in schema.fields
        assert "rules" in schema.fields
        assert "emergency" in schema.fields
        assert "profile_map" in schema.fields


class TestBuiltinProfileSchemaVersions:
    def test_default_profile_has_schema_version_1(self):
        """Default profile embeds schema_version == 1."""
        from config_engine.defaults import build_default_profile
        profile = build_default_profile()
        assert profile["runtime"]["schema_version"] == 1

    def test_all_builtin_profiles_have_schema_version_1(self):
        """Every BUILTIN_PROFILES entry embeds schema_version == 1 in runtime."""
        from config_engine.defaults import BUILTIN_PROFILES
        for name, factory in BUILTIN_PROFILES.items():
            profile = factory()
            runtime = profile.get("runtime", {})
            assert runtime.get("schema_version") == 1, (
                f"Profile {name!r} runtime schema_version={runtime.get('schema_version')}"
            )

    def test_builtin_profile_count(self):
        """Exactly 8 built-in profiles are defined."""
        from config_engine.defaults import BUILTIN_PROFILES
        assert len(BUILTIN_PROFILES) == 8
        expected = {"default", "minimal", "development", "portable", "production", "termux", "desktop-linux", "windows"}
        assert set(BUILTIN_PROFILES.keys()) == expected

    def test_production_profile_sets_restrictive_defaults(self):
        """Production profile sets restrictive defaults consistent with hardening."""
        from config_engine.defaults import BUILTIN_PROFILES
        prod = BUILTIN_PROFILES["production"]()
        assert prod["runtime"]["log_level"] == "warning"
        assert prod["broker"]["mutating_actions_enabled"] is False
        assert prod["broker"]["audit_enabled"] is True
        assert prod["services"]["max_failed_restarts"] == 2
        assert prod["vault"]["max_unlock_attempts"] == 3
        assert prod["vault"]["auto_lock_seconds"] == 60

    def test_minimal_profile_is_readonly(self):
        """Minimal profile disables mutating actions."""
        from config_engine.defaults import BUILTIN_PROFILES
        minimal = BUILTIN_PROFILES["minimal"]()
        assert minimal["broker"]["mutating_actions_enabled"] is False
        assert minimal["operations_center"]["max_source_workers"] == 2

    def test_development_profile_allows_more_restarts(self):
        """Development profile allows more restarts for debugging."""
        from config_engine.defaults import BUILTIN_PROFILES
        dev = BUILTIN_PROFILES["development"]()
        assert dev["services"]["max_failed_restarts"] == 5

    def test_termux_profile_points_to_repo_services(self):
        """Termux profile points manifest_dirs to repo services directory."""
        from config_engine.defaults import BUILTIN_PROFILES
        termux = BUILTIN_PROFILES["termux"]()
        assert "${repo}/Hive Ops Final/etc/services.d" in termux["services"]["manifest_dirs"]

    def test_schema_version_is_always_integer_1(self):
        """All schema_version values across registry and profiles are int 1, not string."""
        from config_engine.defaults import build_registry, BUILTIN_PROFILES
        registry = build_registry()
        for name in registry._schemas:
            schema = registry.get(name)
            fs = schema.fields["schema_version"]
            assert isinstance(fs.default, int), f"Schema {name} default type={type(fs.default)}"
            assert fs.default == 1
        for pname, factory in BUILTIN_PROFILES.items():
            profile = factory()
            sv = profile["runtime"]["schema_version"]
            assert isinstance(sv, int), f"Profile {pname} runtime schema_version type={type(sv)}"
            assert sv == 1