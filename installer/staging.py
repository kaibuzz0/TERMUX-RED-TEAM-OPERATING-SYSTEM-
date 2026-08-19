"""Staged installation: copy source into an isolated staging directory."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from installer.journal import InstallJournal
from installer.schema import InstallPlan, Operation

class StagingError(Exception):
    """Staging operation failure."""



class StagingArea:
    """Isolated staging area for one installation transaction."""

    EXCLUDED_NAMES = {".git", "__pycache__", ".pytest_cache", "node_modules", ".env", "config.yaml"}

    def __init__(self, plan: InstallPlan):
        self.plan = plan
        self.staging_root = plan.target.staging_root / plan.transaction_id
        self.manifest: list[dict[str, Any]] = []
        self.journal = InstallJournal(plan.target.state_root / "install-journal", plan.transaction_id)

    def _validate_containment(self, path: Path) -> None:
        resolved = path.resolve()
        base = self.staging_root.resolve()
        try:
            resolved.relative_to(base)
        except ValueError:
            raise StagingError(f"Path escapes staging root: {path}")

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def create_manifest(self, source_dir: Path) -> list[dict[str, Any]]:
        """Create a source manifest without writing outside the staging area."""
        manifest = []
        for p in sorted(source_dir.rglob("*")):
            rel = p.relative_to(source_dir).as_posix()
            if any(part in self.EXCLUDED_NAMES for part in p.relative_to(source_dir).parts):
                continue
            entry: dict[str, Any] = {
                "path": rel,
                "type": "directory" if p.is_dir() else "file",
                "size": p.stat().st_size if p.is_file() else 0,
                "executable": p.is_file() and (p.stat().st_mode & 0o111) != 0,
            }
            if p.is_file():
                entry["sha256"] = self._hash_file(p)
            manifest.append(entry)
        self.manifest = manifest
        return manifest

    def stage_operation(self, op: Operation) -> None:
        """Execute a single staging operation."""
        self.journal.start() if self.journal._sequence == 0 else None

        if op.op_type == "mkdir":
            assert op.destination is not None
            self._validate_containment(op.destination)
            op.destination.mkdir(parents=True, exist_ok=True)
            self.journal.append(op.op_id, op.op_type, {"destination": str(op.destination)}, result="completed")
        elif op.op_type == "copy":
            assert op.source is not None and op.destination is not None
            self._validate_containment(op.destination)
            if op.destination.exists() and not op.overwrite:
                raise StagingError(f"Destination already exists and overwrite is false: {op.destination}")
            if op.source.is_dir():
                # Avoid staging deep historical/reference trees that cause Windows path-length
                # failures and bloat release payloads.
                _STAGING_IGNORED = {
                    ".git", ".github", "__pycache__", ".pytest_cache", "node_modules",
                    "blueprints",  # exclude entire blueprints tree from runtime payload
                    "evidence",    # exclude historical release evidence from runtime payload
                }

                def _ignore_staging(src: str, names: list[str]) -> set[str]:
                    return set(names) & _STAGING_IGNORED

                shutil.copytree(op.source, op.destination, dirs_exist_ok=op.overwrite, ignore=_ignore_staging)
            else:
                op.destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(op.source, op.destination)
            self.journal.append(op.op_id, op.op_type, {"source": str(op.source), "destination": str(op.destination)}, result="completed")
        elif op.op_type == "write_manifest":
            assert op.destination is not None
            self._validate_containment(op.destination)
            op.destination.parent.mkdir(parents=True, exist_ok=True)
            with open(op.destination, "w", encoding="utf-8") as f:
                json.dump({"manifest": self.manifest, "transaction_id": self.plan.transaction_id}, f, indent=2)
            self.journal.append(op.op_id, op.op_type, {"destination": str(op.destination)}, result="completed")
        else:
            raise StagingError(f"Unsupported operation type: {op.op_type}")

    def stage_all(self) -> Path:
        """Stage the full plan."""
        for op in self.plan.operations:
            self.stage_operation(op)
        # After runtime copy, generate manifest relative to the staging root.
        runtime_copy = self.staging_root / "data" / "runtime"
        self.create_manifest(runtime_copy)
        # Re-write manifest file with staged-relative paths.
        manifest_path = self.staging_root / "state" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"manifest": self.manifest, "transaction_id": self.plan.transaction_id}, f, indent=2)
        self.journal.append("write-manifest", "write_manifest", {"destination": str(manifest_path)}, result="completed")
        self.journal.close("completed")
        return self.staging_root

    def rollback(self) -> None:
        """Roll back staged operations in reverse order using the plan."""
        for op in reversed(self.plan.rollback_operations):
            if op.op_type in ("remove", "rmdir") and op.destination:
                if op.destination.exists():
                    if op.destination.is_dir():
                        shutil.rmtree(op.destination)
                    else:
                        op.destination.unlink()
            self.journal.append(f"rollback-{op.op_id}", op.op_type, {"destination": str(op.destination)}, result="completed")
        self.journal.close("rolled_back")
