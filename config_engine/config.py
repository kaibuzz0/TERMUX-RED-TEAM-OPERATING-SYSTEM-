"""Core Configuration Engine."""

from __future__ import annotations

import getpass
import os
import tempfile
from pathlib import Path
from typing import Any

from config_engine.audit import ConfigAuditLog
from config_engine.defaults import build_default_profile, build_registry
from config_engine.environment import get_env_overrides
from config_engine.errors import ConfigError, ConfigValidationError
from config_engine.loader import load_config_file
from config_engine.merger import build_context, merge_layers, substitute_variables
from config_engine.migration import MIGRATIONS
from config_engine.persistence import ConfigurationStore
from config_engine.preview import format_preview
from config_engine.profiles import ProfileResolver
from config_engine.schema import SchemaRegistry
from config_engine.transactions import CallableFactory, TransactionManager
from config_engine.validator import validate_subsystem_config


# Module-level engine cache for get_config()
_engine: ConfigEngine | None = None


def _default_home() -> Path:
    return Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/")


class ConfigEngine:
    """Single authority for all Hive OS configuration."""

    def __init__(
        self,
        repo_root: Path,
        profile_name: str = "default",
        profile: str | None = None,
        home: Path | None = None,
        config_root: Path | None = None,
        state_root: Path | None = None,
        schemas: SchemaRegistry | None = None,
        env: dict[str, str] | None = None,
    ):
        self.repo_root = repo_root.resolve()
        self.home = (home or _default_home()).resolve()
        self.profile_name = profile or profile_name
        self.schemas = schemas or build_registry()
        self.env = env or os.environ
        self.profile_resolver = ProfileResolver()

        # Determine roots from environment or profile
        env_overrides = get_env_overrides(self.env)
        runtime_defaults = {
            "config_root": str(config_root) if config_root else str(self.home / ".config" / "hive"),
            "state_root": str(state_root) if state_root else str(self.home / ".local" / "state" / "hive"),
        }
        if env_overrides.get("config_root"):
            runtime_defaults["config_root"] = env_overrides["config_root"]
        if env_overrides.get("state_root"):
            runtime_defaults["state_root"] = env_overrides["state_root"]

        self.config_root = Path(runtime_defaults["config_root"])
        self.state_root = Path(runtime_defaults["state_root"])
        self.store = ConfigurationStore(self.config_root, self.state_root)
        self.audit = ConfigAuditLog(self.state_root / "config_audit.jsonl")
        self.txn = TransactionManager(self.store, validate_fn=CallableFactory(self._validate_full_config))

    @classmethod
    def from_repo_root(cls, repo_root: Path | str | None = None, profile: str | None = None) -> "ConfigEngine":
        """Create an engine from a repository root, honoring HIVE_REPO_ROOT."""
        env_root = os.environ.get("HIVE_REPO_ROOT")
        if env_root:
            repo_root = env_root
        if repo_root is None:
            # Walk upward from cwd
            cwd = Path(os.getcwd()).resolve()
            for candidate in [cwd, *cwd.parents]:
                if (candidate / "hive-canonical.json").exists():
                    repo_root = candidate
                    break
            else:
                raise ConfigError("Cannot locate repository root; set HIVE_REPO_ROOT")
        return cls(Path(repo_root), profile_name=profile or os.environ.get("HIVE_PROFILE", "default"))

    def full_config(self) -> dict[str, Any]:
        """Return the fully resolved and validated configuration for all subsystems."""
        return self._build_config()

    def get_config(self, subsystem: str) -> dict[str, Any]:
        """Return typed, validated configuration for a single subsystem."""
        full = self._build_config()
        if subsystem not in full:
            raise ConfigError(f"Subsystem not configured: {subsystem}")
        return full[subsystem]

    def _build_config(self) -> dict[str, Any]:
        # 1. Hive defaults
        defaults = build_default_profile()

        # 2. Platform defaults (currently just default; future: detect platform)
        platform_defaults = {}

        # 3. Profile layer
        profile_layer = self.profile_resolver.resolve(self.profile_name)

        # 4. User configuration files
        user_layer = self._load_user_layer()

        # 5. Environment overrides
        env_layer = self._build_env_layer()

        # Merge layers
        merged = merge_layers(defaults, platform_defaults)
        merged = merge_layers(merged, profile_layer)
        merged = merge_layers(merged, user_layer)
        merged = merge_layers(merged, env_layer)

        # Validate runtime first to establish context
        runtime_schema = self.schemas.get("runtime")
        runtime_raw = merged.get("runtime", {})
        runtime_cfg = runtime_schema.validate(runtime_raw)
        runtime_cfg = self._apply_runtime_substitutions(runtime_cfg)

        # Build substitution context
        context = build_context(runtime_cfg, self.repo_root, self.home, tempfile.gettempdir())

        # Resolve each subsystem
        result: dict[str, Any] = {}
        errors: list[dict] = []
        all_warnings: list[dict] = []
        for name, schema in self.schemas._schemas.items():
            raw = merged.get(name, {})
            try:
                migrated, migrations = MIGRATIONS.migrate(name, raw, schema.version)
                validated = schema.validate(migrated)
                # Substitute variables
                substituted = substitute_variables(validated, context)
                # Strip internal keys from public config but keep warnings
                warnings = substituted.pop("_warnings", [])
                all_warnings.extend(warnings)
                # Run cross-field validation
                cross_errors = validate_subsystem_config(name, substituted, runtime_cfg)
                if cross_errors:
                    errors.extend(cross_errors)
                # Mark migration performed
                if migrations:
                    substituted["_migration_performed"] = migrations
                result[name] = substituted
            except ConfigValidationError as e:
                errors.append({"subsystem": name, "message": str(e), "details": e.details})
            except Exception as e:
                errors.append({"subsystem": name, "message": str(e)})

        if errors:
            raise ConfigValidationError("Configuration resolution failed", details=errors)

        result["_meta"] = {
            "version": 1,
            "profile": self.profile_name,
            "schema_registry_version": 1,
            "warnings": all_warnings,
        }
        return result

    def _apply_runtime_substitutions(self, runtime: dict[str, Any]) -> dict[str, Any]:
        """Resolve runtime paths before building the global context."""
        context = {
            "home": str(self.home),
            "tmp": tempfile.gettempdir(),
            "repo": str(self.repo_root),
        }
        for k, v in runtime.items():
            if isinstance(v, str) and "${" in v:
                runtime[k] = _resolve_simple(v, context)
        return runtime

    def _load_user_layer(self) -> dict[str, Any]:
        """Load user configuration files if they exist."""
        path = self.config_root / "config.json"
        if not path.exists():
            return {}
        try:
            return load_config_file(path)
        except ConfigError:
            return {}

    def _build_env_layer(self) -> dict[str, Any]:
        """Convert allowed environment variables into a runtime fragment."""
        overrides = get_env_overrides(self.env)
        if not overrides:
            return {}
        layer: dict[str, Any] = {"runtime": {}}
        runtime = layer["runtime"]
        if "profile" in overrides:
            runtime["profile"] = overrides["profile"]
            self.profile_name = overrides["profile"]
        if "config_root" in overrides:
            runtime["config_root"] = overrides["config_root"]
        if "state_root" in overrides:
            runtime["state_root"] = overrides["state_root"]
        if "log_root" in overrides:
            runtime["log_root"] = overrides["log_root"]
        if "data_root" in overrides:
            runtime["data_root"] = overrides["data_root"]
        if "cache_root" in overrides:
            runtime["cache_root"] = overrides["cache_root"]
        if "temp_root" in overrides:
            runtime["temp_root"] = overrides["temp_root"]
        if "legacy_root" in overrides:
            runtime["legacy_root"] = overrides["legacy_root"]
        if "repo_root" in overrides:
            runtime["repo_root"] = overrides["repo_root"]
        return layer

    def _validate_full_config(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Validate a full configuration candidate."""
        # Build a temporary engine-like validation pass
        errors: list[dict] = []
        runtime_raw = candidate.get("runtime", {})
        try:
            runtime_cfg = self.schemas.get("runtime").validate(runtime_raw)
        except ConfigValidationError as e:
            errors.extend(e.details)
            raise ConfigValidationError("Full config validation failed", details=errors)

        runtime_cfg = self._apply_runtime_substitutions(runtime_cfg)
        context = build_context(runtime_cfg, self.repo_root, self.home, tempfile.gettempdir())

        for name, schema in self.schemas._schemas.items():
            if name == "runtime":
                continue
            raw = candidate.get(name, {})
            try:
                migrated, _ = MIGRATIONS.migrate(name, raw, schema.version)
                validated = schema.validate(migrated)
                substituted = substitute_variables(validated, context)
                substituted.pop("_warnings", None)
                cross = validate_subsystem_config(name, substituted, runtime_cfg)
                errors.extend(cross)
            except ConfigValidationError as e:
                errors.extend(e.details)

        if errors:
            raise ConfigValidationError("Full config validation failed", details=errors)
        return candidate


    def explain(self, subsystem: str, field: str | None = None) -> dict[str, Any]:
        """Explain the source of a resolved configuration field."""
        layers = self._build_layer_map()
        selected = layers.get(subsystem, {})
        resolved = self.get_config(subsystem)
        if field is None:
            return {
                "subsystem": subsystem,
                "fields": {
                    k: {"source": selected.get(k, {}).get("source", "DEFAULT"), "value": _redact_for_display(resolved.get(k))}
                    for k in resolved
                },
            }
        source = selected.get(field, {}).get("source", "DEFAULT")
        value = _redact_for_display(resolved.get(field))
        return {"subsystem": subsystem, "field": field, "source": source, "value": value}

    def show_with_sources(self, subsystem: str) -> dict[str, Any]:
        """Return resolved subsystem configuration annotated with source provenance."""
        cfg = self.get_config(subsystem)
        provenance = self.explain(subsystem)
        return {
            "subsystem": subsystem,
            "data": _redact_for_display(cfg),
            "sources": {k: v["source"] for k, v in provenance.get("fields", {}).items()},
        }

    def _build_layer_map(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Build a map of every subsystem field to its winning layer."""
        defaults = build_default_profile()
        platform_defaults: dict[str, Any] = {}
        profile_layer = self.profile_resolver.resolve(self.profile_name)
        user_layer = self._load_user_layer()
        env_layer = self._build_env_layer()

        layer_stack = [
            ("DEFAULT", defaults),
            ("PLATFORM_DEFAULT", platform_defaults),
            ("PROFILE", profile_layer),
            ("USER_CONFIG", user_layer),
            ("ENVIRONMENT_OVERRIDE", env_layer),
        ]

        result: dict[str, dict[str, dict[str, Any]]] = {}
        for source_name, layer in layer_stack:
            for subsys, values in layer.items():
                if not isinstance(values, dict):
                    continue
                result.setdefault(subsys, {})
                for field, value in values.items():
                    # Field must be known to schema or a runtime-level field
                    result[subsys][field] = {"source": source_name, "value": value}
        return result


    def commit(self, candidate: dict[str, Any], author: str | None = None) -> dict[str, Any]:
        """Commit a full configuration candidate atomically."""
        author = author or getpass.getuser()
        result = self.txn.commit(candidate, self.profile_name, author, candidate.get("_migration_performed", []))
        self.audit.record(
            result["transaction_id"],
            "commit",
            self.profile_name,
            author,
            {"version": result.get("version")},
        )
        return result

    def preview_commit(self, candidate: dict[str, Any]) -> str:
        """Return a dry-run preview of committing a candidate."""
        previous = self.store.load_committed()
        preview = self.txn.preview(previous, candidate)
        return format_preview(preview, as_json=True)

    def history(self) -> list[dict[str, Any]]:
        """Return configuration transaction history."""
        return self.store.list_transactions()

    def rollback(self, txn_id: str, author: str | None = None) -> dict[str, Any]:
        """Rollback to a historical transaction."""
        author = author or getpass.getuser()
        result = self.txn.rollback(txn_id, author)
        self.audit.record(
            result["transaction_id"],
            "rollback",
            result.get("profile", self.profile_name),
            author,
            {"restored_transaction": txn_id},
        )
        return result

    def schema_info(self, name: str | None = None) -> dict[str, Any]:
        """Return schema metadata."""
        if name:
            schema = self.schemas.get(name)
            return {
                "name": schema.name,
                "version": schema.version,
                "extensible": schema.extensible,
                "fields": {k: {"type": str(v.type), "required": v.required, "deprecated": v.deprecated} for k, v in schema.fields.items()},
            }
        return {"schemas": self.schemas.list()}


def _resolve_simple(value: str, context: dict[str, str]) -> str:
    """Resolve simple ${key} or ${section:key} variables."""
    import re
    pattern = re.compile(r"\$\{([^}]+)\}")

    def repl(match: re.Match) -> str:
        key = match.group(1)
        if key in context:
            return context[key]
        if ":" in key:
            section, sub = key.split(":", 1)
            composite = f"{section}:{sub}"
            if composite in context:
                return context[composite]
        if key in os.environ:
            return os.environ[key]
        raise ConfigValidationError(f"Unresolved variable: ${{{key}}}")

    return pattern.sub(repl, value)


def _redact_for_display(value: Any) -> Any:
    """Recursively redact secret-like values for display."""
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if any(s in k.lower() for s in ("secret", "password", "key", "token", "credential")) else _redact_for_display(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_for_display(v) for v in value]
    return value


def get_config(subsystem: str, repo_root: Path | str | None = None, profile: str | None = None) -> dict[str, Any]:
    """Global helper: obtain validated configuration for a subsystem.

    This is the stable interface all subsystems should use after Milestone 14.
    """
    global _engine
    if _engine is None:
        _engine = ConfigEngine.from_repo_root(repo_root, profile)
    return _engine.get_config(subsystem)
