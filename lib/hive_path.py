"""Central path resolution for Hive OS.

This module is transitional infrastructure for Milestone 3.
It resolves repository-relative paths from a validated repository root and
provides the future Hive state-directory model without creating or moving data.
"""

import json
import os
from pathlib import Path


METADATA_FILE = "hive-canonical.json"
REQUIRED_METADATA_KEYS = {
    "schema_version",
    "current_canonical_source",
    "current_canonical_launcher",
    "current_canonical_launcher_type",
    "launcher_execution_policy",
}
ALLOWED_LAUNCHER_TYPES = {"python", "bash", "posix-shell", "direct-executable"}
ALLOWED_EXECUTION_POLICIES = {"explicit-interpreter", "direct-execution"}


def resolve_repository_root(from_path: Path | str | None = None) -> Path:
    """Resolve repository root from a path inside the repository.

    Defaults to the current working directory. Walks upward until
    hive-canonical.json is found or filesystem root is reached.
    """
    start = Path(from_path or os.getcwd()).resolve()
    if start.is_file():
        start = start.parent

    for candidate in [start, *start.parents]:
        if (candidate / METADATA_FILE).is_file():
            return candidate

    raise PathResolutionError(f"could not locate repository root from {start}")


class PathResolutionError(ValueError):
    """Raised when a path cannot be resolved safely."""


class CanonicalMetadataError(ValueError):
    """Raised when canonical metadata is missing or invalid."""


class LauncherTypeError(ValueError):
    """Raised when the launcher type is unsupported or mismatched."""


def load_metadata(repo_root: Path) -> dict:
    """Load and validate hive-canonical.json."""
    metadata_path = repo_root / METADATA_FILE
    if not metadata_path.is_file():
        raise CanonicalMetadataError(f"missing canonical metadata: {metadata_path}")

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise CanonicalMetadataError(f"malformed canonical metadata: {exc}") from exc

    if not isinstance(data, dict):
        raise CanonicalMetadataError("canonical metadata is not a JSON object")

    missing = REQUIRED_METADATA_KEYS - set(data.keys())
    if missing:
        raise CanonicalMetadataError(f"canonical metadata missing keys: {sorted(missing)}")

    if data.get("schema_version") != 1:
        raise CanonicalMetadataError(f"unsupported schema_version: {data.get('schema_version')}")

    launcher_type = data.get("current_canonical_launcher_type")
    if launcher_type not in ALLOWED_LAUNCHER_TYPES:
        raise LauncherTypeError(
            f"unsupported launcher type {launcher_type!r}; "
            f"allowed: {sorted(ALLOWED_LAUNCHER_TYPES)}"
        )

    policy = data.get("launcher_execution_policy")
    if policy not in ALLOWED_EXECUTION_POLICIES:
        raise LauncherTypeError(
            f"unsupported execution policy {policy!r}; "
            f"allowed: {sorted(ALLOWED_EXECUTION_POLICIES)}"
        )

    return data


def _contained(target: Path, container: Path) -> bool:
    """Return True if target is contained within container, both resolved."""
    try:
        target.resolve().relative_to(container.resolve())
        return True
    except ValueError:
        return False


def resolve_canonical_source(repo_root: Path, metadata: dict | None = None) -> Path:
    """Resolve the current canonical source directory."""
    if metadata is None:
        metadata = load_metadata(repo_root)

    source_name = metadata["current_canonical_source"]
    if not isinstance(source_name, str) or not source_name:
        raise CanonicalMetadataError("current_canonical_source must be a non-empty string")

    source = (repo_root / source_name).resolve()
    if not source.is_dir():
        raise CanonicalMetadataError(f"canonical source directory not found: {source}")

    if not _contained(source, repo_root):
        raise CanonicalMetadataError(f"canonical source escapes repository: {source}")

    return source


def resolve_canonical_launcher(repo_root: Path, metadata: dict | None = None) -> Path:
    """Resolve and validate the current canonical launcher."""
    if metadata is None:
        metadata = load_metadata(repo_root)

    launcher_rel = metadata["current_canonical_launcher"]
    if not isinstance(launcher_rel, str) or not launcher_rel:
        raise CanonicalMetadataError("current_canonical_launcher must be a non-empty string")

    target = (repo_root / launcher_rel).resolve()
    source = resolve_canonical_source(repo_root, metadata)

    if not _contained(target, repo_root):
        raise PathResolutionError(f"canonical launcher escapes repository: {target}")

    if not _contained(target, source):
        raise PathResolutionError(
            f"canonical launcher is not inside canonical source {source}: {target}"
        )

    if not target.is_file():
        raise PathResolutionError(f"canonical launcher not found: {target}")

    return target




def resolve_config_root(prefix: Path | None = None, home: Path | None = None, env_override: str = "HIVE_CONFIG_ROOT") -> Path:
    """Resolve the user configuration root."""
    if env_override and os.environ.get(env_override):
        p = Path(os.environ.get(env_override))
        if not p.is_absolute():
            raise PathResolutionError(f"{env_override} must be absolute: {p}")
        return p
    home = home or Path(os.environ.get("HOME") or "/")
    return home / ".config" / "hive"


def resolve_state_root(prefix: Path | None = None, home: Path | None = None, env_override: str = "HIVE_STATE_ROOT") -> Path:
    """Resolve the mutable runtime state root."""
    if env_override and os.environ.get(env_override):
        p = Path(os.environ.get(env_override))
        if not p.is_absolute():
            raise PathResolutionError(f"{env_override} must be absolute: {p}")
        return p
    home = home or Path(os.environ.get("HOME") or "/")
    return home / ".local" / "state" / "hive"


def resolve_data_root(prefix: Path | None = None, home: Path | None = None, env_override: str = "HIVE_DATA_ROOT") -> Path:
    """Resolve persistent Hive-owned application data root."""
    if env_override and os.environ.get(env_override):
        p = Path(os.environ.get(env_override))
        if not p.is_absolute():
            raise PathResolutionError(f"{env_override} must be absolute: {p}")
        return p
    home = home or Path(os.environ.get("HOME") or "/")
    return home / ".local" / "share" / "hive"


def resolve_cache_root(prefix: Path | None = None, home: Path | None = None, env_override: str = "HIVE_CACHE_ROOT") -> Path:
    """Resolve disposable cache root."""
    if env_override and os.environ.get(env_override):
        p = Path(os.environ.get(env_override))
        if not p.is_absolute():
            raise PathResolutionError(f"{env_override} must be absolute: {p}")
        return p
    home = home or Path(os.environ.get("HOME") or "/")
    return home / ".cache" / "hive"


def resolve_log_root(prefix: Path | None = None, home: Path | None = None, env_override: str = "HIVE_LOG_ROOT") -> Path:
    """Resolve bounded log root."""
    if env_override and os.environ.get(env_override):
        p = Path(os.environ.get(env_override))
        if not p.is_absolute():
            raise PathResolutionError(f"{env_override} must be absolute: {p}")
        return p
    return resolve_state_root(prefix, home) / "logs"


def resolve_temp_root(prefix: Path | None = None, env_override: str = "HIVE_TEMP_ROOT") -> Path:
    """Resolve validated temporary root."""
    if env_override and os.environ.get(env_override):
        p = Path(os.environ.get(env_override))
        if not p.is_absolute():
            raise PathResolutionError(f"{env_override} must be absolute: {p}")
        return p
    tmp = os.environ.get("TMPDIR") or os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"
    return Path(tmp) / "hive"


def resolve_legacy_root(env_override: str = "HIVE_LEGACY_ROOT") -> Path:
    """Return the legacy /root/hive path for compatibility checks only."""
    if env_override and os.environ.get(env_override):
        p = Path(os.environ.get(env_override))
        if not p.is_absolute():
            raise PathResolutionError(f"{env_override} must be absolute: {p}")
        return p
    return Path("/root/hive")


def ensure_inside_repo(path: Path, repo_root: Path | None = None) -> None:
    """Raise RuntimeError if *path* resolves outside the repository.

    This is a centralized guard to prevent staged files or resolved paths from
    escaping the project tree.  It is intentionally conservative: any path that
    cannot be proven to live under *repo_root* is rejected.
    """
    target = Path(path).resolve()
    root = repo_root.resolve() if repo_root else resolve_repository_root()
    try:
        target.relative_to(root)
    except ValueError:
        raise RuntimeError(f"Path escapes repository root: {path}")


def resolve_future_state_dirs(prefix: Path | None = None, home: Path | None = None) -> dict:
    """Return the future Hive state-directory model without creating them.

    On Termux, prefix defaults to $PREFIX and home to $HOME.
    On other platforms, prefix may be None.
    """
    home_path = home or Path(os.environ.get("HOME", "/"))
    prefix_path = prefix or (Path(p) if (p := os.environ.get("PREFIX")) else None)

    return {
        "home": home_path,
        "prefix": prefix_path,
        "config_dir": home_path / ".config" / "hive",
        "state_dir": home_path / ".local" / "state" / "hive",
        "data_dir": home_path / ".local" / "share" / "hive",
        "cache_dir": home_path / ".cache" / "hive",
        "runtime_dir": prefix_path / "var" / "run" / "hive" if prefix_path else None,
    }
