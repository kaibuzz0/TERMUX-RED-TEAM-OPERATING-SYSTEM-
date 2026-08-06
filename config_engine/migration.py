"""Configuration migration engine for schema evolution."""

from __future__ import annotations

from typing import Any, Callable

from config_engine.errors import ConfigMigrationError


MigrationStep = Callable[[dict[str, Any]], dict[str, Any]]


class Migration:
    """A single named migration step."""

    def __init__(self, name: str, from_version: int, to_version: int, transform: MigrationStep):
        self.name = name
        self.from_version = from_version
        self.to_version = to_version
        self.transform = transform


class MigrationRegistry:
    """Registry of migrations per subsystem."""

    def __init__(self) -> None:
        self._migrations: dict[str, list[Migration]] = {}

    def register(self, subsystem: str, migration: Migration) -> None:
        self._migrations.setdefault(subsystem, [])
        for existing in self._migrations[subsystem]:
            if existing.name == migration.name:
                raise ConfigMigrationError(f"Duplicate migration {migration.name!r} for {subsystem}")
        self._migrations[subsystem].append(migration)
        self._migrations[subsystem].sort(key=lambda m: m.from_version)

    def migrate(
        self,
        subsystem: str,
        data: dict[str, Any],
        target_version: int,
    ) -> tuple[dict[str, Any], list[str]]:
        """Migrate a subsystem configuration to target_version.

        Returns (migrated_data, performed_migration_names).
        """
        current = data.get("schema_version", 1)
        if current == target_version:
            return data, []
        if current > target_version:
            raise ConfigMigrationError(
                f"Schema downgrade not allowed for {subsystem}: {current} -> {target_version}"
            )

        migrations = self._migrations.get(subsystem, [])
        working = dict(data)
        performed = []
        for migration in migrations:
            if migration.from_version == current and migration.to_version <= target_version:
                working = migration.transform(working)
                if working.get("schema_version") != migration.to_version:
                    raise ConfigMigrationError(
                        f"Migration {migration.name} did not update schema_version to {migration.to_version}"
                    )
                current = working["schema_version"]
                performed.append(migration.name)
                if current == target_version:
                    break

        if current != target_version:
            raise ConfigMigrationError(
                f"Could not migrate {subsystem} from version {data.get('schema_version', 1)} to {target_version}"
            )

        return working, performed

    def list_migrations(self, subsystem: str) -> list[str]:
        return [m.name for m in self._migrations.get(subsystem, [])]


# Canonical migration examples
MIGRATIONS = MigrationRegistry()


def _register_builtin_migrations() -> None:
    # Runtime migration example: rename log_directory to log_root
    MIGRATIONS.register(
        "runtime",
        Migration(
            "runtime-rename-log-directory",
            1,
            2,
            lambda d: _rename_key(d, "log_directory", "log_root"),
        ),
    )
    # Broker migration example: split timeout into default_timeout_seconds
    MIGRATIONS.register(
        "broker",
        Migration(
            "broker-split-timeout",
            1,
            2,
            lambda d: _rename_key(d, "timeout_seconds", "default_timeout_seconds"),
        ),
    )


def _rename_key(data: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    result = dict(data)
    if old in result:
        result[new] = result.pop(old)
    if "schema_version" in result:
        result["schema_version"] = result["schema_version"] + 1
    return result


_register_builtin_migrations()
