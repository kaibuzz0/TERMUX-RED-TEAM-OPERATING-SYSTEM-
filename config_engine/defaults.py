"""Default configuration values and built-in schemas."""

from __future__ import annotations

from config_engine.schema import ConfigSchema, FieldSpec, SchemaRegistry


def build_registry() -> SchemaRegistry:
    """Build the canonical Hive OS schema registry."""
    registry = SchemaRegistry()

    # Runtime schema
    registry.register(ConfigSchema(
        name="runtime",
        version=1,
        fields={
            "schema_version": FieldSpec("schema_version", int, required=True, min_value=1, default=1),
            "profile": FieldSpec("profile", str, required=True, default="default"),
            "log_level": FieldSpec("log_level", str, default="info", allowed_values={"debug", "info", "warning", "error"}),
            "log_root": FieldSpec("log_root", str, default="${home}/.local/state/hive/logs"),
            "state_root": FieldSpec("state_root", str, default="${home}/.local/state/hive"),
            "config_root": FieldSpec("config_root", str, default="${home}/.config/hive"),
            "data_root": FieldSpec("data_root", str, default="${home}/.local/share/hive"),
            "cache_root": FieldSpec("cache_root", str, default="${home}/.cache/hive"),
            "temp_root": FieldSpec("temp_root", str, default="${tmp}/hive"),
            "max_log_size_mb": FieldSpec("max_log_size_mb", int, default=10, min_value=1, max_value=1024),
            "max_log_count": FieldSpec("max_log_count", int, default=5, min_value=1, max_value=100),
        },
    ))

    # Broker schema
    registry.register(ConfigSchema(
        name="broker",
        version=1,
        fields={
            "schema_version": FieldSpec("schema_version", int, required=True, default=1),
            "state_root": FieldSpec("state_root", str, default="${runtime:state_root}"),
            "log_root": FieldSpec("log_root", str, default="${runtime:log_root}"),
            "default_timeout_seconds": FieldSpec("default_timeout_seconds", int, default=30, min_value=1, max_value=3600),
            "max_active_transactions": FieldSpec("max_active_transactions", int, default=10, min_value=1, max_value=100),
            "audit_enabled": FieldSpec("audit_enabled", bool, default=True),
            "mutating_actions_enabled": FieldSpec("mutating_actions_enabled", bool, default=False),
            "policy_profile": FieldSpec("policy_profile", str, default="observer"),
        },
    ))

    # Services schema
    registry.register(ConfigSchema(
        name="services",
        version=1,
        fields={
            "schema_version": FieldSpec("schema_version", int, required=True, default=1),
            "manifest_dirs": FieldSpec("manifest_dirs", list, default=["${repo}/Hive Ops Final/etc/services.d"]),
            "user_override_dirs": FieldSpec("user_override_dirs", list, default=["${config_root}/services.d"]),
            "state_root": FieldSpec("state_root", str, default="${runtime:state_root}"),
            "log_root": FieldSpec("log_root", str, default="${runtime:log_root}"),
            "max_failed_restarts": FieldSpec("max_failed_restarts", int, default=3, min_value=0, max_value=20),
            "backoff_base_seconds": FieldSpec("backoff_base_seconds", int, default=1, min_value=0, max_value=300),
            "backoff_max_seconds": FieldSpec("backoff_max_seconds", int, default=60, min_value=1, max_value=3600),
            "shutdown_timeout_seconds": FieldSpec("shutdown_timeout_seconds", int, default=10, min_value=1, max_value=300),
            "enable_legacy_adapter": FieldSpec("enable_legacy_adapter", bool, default=True),
        },
    ))

    # Vault schema
    registry.register(ConfigSchema(
        name="vault",
        version=1,
        fields={
            "schema_version": FieldSpec("schema_version", int, required=True, default=1),
            "backend": FieldSpec("backend", str, default="file", allowed_values={"file", "memory"}),
            "path": FieldSpec("path", str, default="${runtime:state_root}/vault"),
            "max_unlock_attempts": FieldSpec("max_unlock_attempts", int, default=5, min_value=1, max_value=100),
            "key_derivation": FieldSpec("key_derivation", str, default="argon2", allowed_values={"argon2", "pbkdf2"}),
            "auto_lock_seconds": FieldSpec("auto_lock_seconds", int, default=300, min_value=0, max_value=86400),
        },
    ))

    # Updates schema
    registry.register(ConfigSchema(
        name="updates",
        version=1,
        fields={
            "schema_version": FieldSpec("schema_version", int, required=True, default=1),
            "trust_store": FieldSpec("trust_store", str, default="${config_root}/trust"),
            "update_cache": FieldSpec("update_cache", str, default="${runtime:cache_root}/updates"),
            "max_bundle_size_mb": FieldSpec("max_bundle_size_mb", int, default=100, min_value=1, max_value=4096),
            "signature_required": FieldSpec("signature_required", bool, default=True),
            "anti_rollback": FieldSpec("anti_rollback", bool, default=True),
            "rollback_on_failure": FieldSpec("rollback_on_failure", bool, default=True),
            "max_sequence_delta": FieldSpec("max_sequence_delta", int, default=1000, min_value=1, max_value=1000000),
        },
    ))

    # Recovery schema
    registry.register(ConfigSchema(
        name="recovery",
        version=1,
        fields={
            "schema_version": FieldSpec("schema_version", int, required=True, default=1),
            "journal_dir": FieldSpec("journal_dir", str, default="${runtime:state_root}/recovery"),
            "max_journal_entries": FieldSpec("max_journal_entries", int, default=100, min_value=1, max_value=10000),
            "auto_snapshot": FieldSpec("auto_snapshot", bool, default=True),
            "snapshot_dir": FieldSpec("snapshot_dir", str, default="${runtime:state_root}/snapshots"),
            "max_snapshots": FieldSpec("max_snapshots", int, default=5, min_value=1, max_value=50),
        },
    ))

    # Operations Center schema
    registry.register(ConfigSchema(
        name="operations_center",
        version=1,
        fields={
            "schema_version": FieldSpec("schema_version", int, required=True, default=1),
            "default_timeout_seconds": FieldSpec("default_timeout_seconds", int, default=10, min_value=1, max_value=300),
            "max_source_workers": FieldSpec("max_source_workers", int, default=4, min_value=1, max_value=16),
            "default_view": FieldSpec("default_view", str, default="overview"),
            "redact_secrets": FieldSpec("redact_secrets", bool, default=True),
            "json_indent": FieldSpec("json_indent", int, default=2, min_value=0, max_value=8),
            "enable_diagnostics": FieldSpec("enable_diagnostics", bool, default=True),
        },
    ))

    # Plugin SDK schema placeholder
    registry.register(ConfigSchema(
        name="plugins",
        version=1,
        fields={
            "schema_version": FieldSpec("schema_version", int, required=True, default=1),
            "enabled": FieldSpec("enabled", list, default=[]),
            "plugin_dirs": FieldSpec("plugin_dirs", list, default=["${config_root}/plugins"]),
            "sandbox": FieldSpec("sandbox", str, default="process", allowed_values={"process", "none"}),
            "capability_whitelist": FieldSpec("capability_whitelist", list, default=[]),
            "max_plugin_memory_mb": FieldSpec("max_plugin_memory_mb", int, default=256, min_value=16, max_value=4096),
        },
    ))

    return registry


def build_default_profile() -> dict:
    """Default profile base configuration."""
    return {
        "runtime": {
            "schema_version": 1,
            "profile": "default",
            "log_level": "info",
        },
    }


BUILTIN_PROFILES = {
    "default": build_default_profile,
    "minimal": lambda: {
        "runtime": {"schema_version": 1, "profile": "minimal", "log_level": "warning"},
        "broker": {"mutating_actions_enabled": False, "audit_enabled": True},
        "operations_center": {"default_timeout_seconds": 5, "max_source_workers": 2},
    },
    "development": lambda: {
        "runtime": {"schema_version": 1, "profile": "development", "log_level": "debug"},
        "broker": {"mutating_actions_enabled": False, "audit_enabled": True},
        "services": {"max_failed_restarts": 5},
    },
    "portable": lambda: {
        "runtime": {"schema_version": 1, "profile": "portable", "log_level": "info"},
        "vault": {"backend": "file"},
        "updates": {"trust_store": "${repo}/trusted_keys"},
    },
    "production": lambda: {
        "runtime": {"schema_version": 1, "profile": "production", "log_level": "warning"},
        "broker": {"mutating_actions_enabled": False, "audit_enabled": True},
        "services": {"max_failed_restarts": 2},
        "vault": {"max_unlock_attempts": 3, "auto_lock_seconds": 60},
    },
    "termux": lambda: {
        "runtime": {"schema_version": 1, "profile": "termux", "log_level": "info"},
        "services": {"manifest_dirs": ["${repo}/Hive Ops Final/etc/services.d"]},
        "vault": {"backend": "file", "path": "${runtime:state_root}/vault"},
    },
    "desktop-linux": lambda: {
        "runtime": {"schema_version": 1, "profile": "desktop-linux", "log_level": "info"},
        "services": {"enable_legacy_adapter": False},
    },
    "windows": lambda: {
        "runtime": {"schema_version": 1, "profile": "windows", "log_level": "info"},
        "services": {"enable_legacy_adapter": False, "shutdown_timeout_seconds": 15},
    },
}
