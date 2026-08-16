"""Generate a deterministic, machine-readable installation plan."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

from installer.preflight import run_preflight, PreflightResult
from installer.schema import InstallPlan, InstallStatus, Operation, SourceInfo, TargetPolicy, CapabilityState

try:
    from lib.hive_path import (
        resolve_repository_root,
        resolve_canonical_source,
        resolve_canonical_launcher,
        resolve_config_root,
        resolve_state_root,
        resolve_data_root,
        resolve_cache_root,
        resolve_log_root,
    )
except Exception:
    resolve_repository_root = None


def _get_git_commit(repo_root: Path) -> str:
    import os
    import shutil
    git_cmd = shutil.which("git")
    if git_cmd is None:
        git_cmd = os.environ.get("HIVE_BUNDLED_GIT")
    if git_cmd is None:
        return "unknown:git-not-found"
    try:
        result = subprocess.run(
            [git_cmd, "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"unknown:{e}"


def _get_git_remote(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _load_canonical_metadata(repo_root: Path) -> dict:
    path = repo_root / "hive-canonical.json"
    if not path.exists():
        raise RuntimeError(f"Missing canonical metadata: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _make_target_policy(repo_root: Path, overrides: dict[str, Path] | None = None) -> TargetPolicy:
    if resolve_repository_root is None:
        raise RuntimeError("lib/hive_path.py is required")
    home_value = os.environ.get("HOME")
    if not home_value:
        raise RuntimeError("HOME is required to determine Hive target paths")
    home = Path(home_value)
    overrides = overrides or {}
    return TargetPolicy(
        root=overrides.get("root", resolve_data_root(home=home)),
        config_root=overrides.get("config_root", resolve_config_root(home=home)),
        state_root=overrides.get("state_root", resolve_state_root(home=home)),
        data_root=overrides.get("data_root", resolve_data_root(home=home)),
        cache_root=overrides.get("cache_root", resolve_cache_root(home=home)),
        log_root=overrides.get("log_root", resolve_log_root(home=home)),
        staging_root=overrides.get("staging_root", resolve_state_root(home=home) / "install-staging"),
    )


def _build_operations(plan: InstallPlan) -> list[Operation]:
    """Construct the ordered operation list for a clean install.


    All operations target the staging area; activation maps them to final targets later.
    """
    ops: list[Operation] = []
    staging = plan.target.staging_root / plan.transaction_id

    # 1. Prepare staging subdirectories.
    ops.append(Operation("mkdir-state", "mkdir", destination=staging / "state"))
    ops.append(Operation("mkdir-config", "mkdir", destination=staging / "config"))
    ops.append(Operation("mkdir-data", "mkdir", destination=staging / "data"))
    ops.append(Operation("mkdir-cache", "mkdir", destination=staging / "cache"))
    ops.append(Operation("mkdir-logs", "mkdir", destination=staging / "logs"))

    # 2. Copy canonical source tree into staged runtime copy.
    runtime_copy = staging / "data" / "runtime"
    ops.append(Operation("copy-runtime", "copy", source=plan.source.canonical_source, destination=runtime_copy, overwrite=False))

    # 3. Write a source manifest into staged state.
    manifest_path = staging / "state" / "manifest.json"
    ops.append(Operation("write-manifest", "write_manifest", destination=manifest_path))

    return ops


def _build_rollback_operations(plan: InstallPlan) -> list[Operation]:
    """Generate rollback operations in reverse order."""
    rollback: list[Operation] = []
    for op in reversed(plan.operations):
        if op.op_type == "copy":
            rollback.append(Operation(f"rollback-{op.op_id}", "remove", destination=op.destination))
        elif op.op_type == "mkdir":
            rollback.append(Operation(f"rollback-{op.op_id}", "rmdir", destination=op.destination))
        elif op.op_type == "write_manifest":
            rollback.append(Operation(f"rollback-{op.op_id}", "remove", destination=op.destination))
    return rollback


def generate_plan(repo_root: Path | None = None, target_overrides: dict[str, Path] | None = None, transaction_id: str | None = None) -> InstallPlan:
    """Generate a deterministic installation plan without mutating the system."""
    if resolve_repository_root is None:
        raise RuntimeError("lib/hive_path.py is required for planning")

    if repo_root is None:
        repo_root = resolve_repository_root()

    metadata = _load_canonical_metadata(repo_root)
    canonical = resolve_canonical_source(repo_root)
    launcher = resolve_canonical_launcher(repo_root, metadata)

    preflight = run_preflight(repo_root)

    source = SourceInfo(
        repository=repo_root,
        remote=_get_git_remote(repo_root),
        commit=_get_git_commit(repo_root),
        canonical_source=canonical,
        launcher=launcher,
    )

    target = _make_target_policy(repo_root, target_overrides)

    if transaction_id is None:
        transaction_id = uuid.uuid4().hex

    plan = InstallPlan(
        schema_version=1,
        transaction_id=transaction_id,
        source=source,
        target=target,
        operations=[],
        rollback_required=True,
        existing_status=preflight.existing_installation,
        required_packages=[
            {"name": "git", "category": CapabilityState.AVAILABLE.value if preflight.classification.get("git") == CapabilityState.AVAILABLE else CapabilityState.UNKNOWN.value},
            {"name": "bash", "category": CapabilityState.AVAILABLE.value if preflight.classification.get("bash") == CapabilityState.AVAILABLE else CapabilityState.UNKNOWN.value},
        ],
    )

    plan.operations = _build_operations(plan)
    plan.rollback_operations = _build_rollback_operations(plan)
    plan.proposed_shell_startup_entries = [
        f'export HIVE_HOME="{plan.target.root}"',
        f'export HIVE_CONFIG_ROOT="{plan.target.config_root}"',
        f'export HIVE_STATE_ROOT="{plan.target.state_root}"',
        f'export HIVE_DATA_ROOT="{plan.target.data_root}"',
    ]

    return plan
