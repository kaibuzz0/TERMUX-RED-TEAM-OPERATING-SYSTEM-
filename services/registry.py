"""Service registry: load and classify manifests from approved directories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.errors import ServiceConfigError
from services.schema import load_manifest_file, validate_manifest


class ServiceRegistry:
    """Load native and legacy-adapted service manifests without starting them."""

    def __init__(self, repo_root: Path, state_root: Path, user_config_root: Path | None = None):
        self.repo_root = repo_root
        self.state_root = state_root
        self.user_config_root = user_config_root
        self.native: dict[str, dict[str, Any]] = {}
        self.legacy_only: dict[str, dict[str, Any]] = {}
        self.unsupported: list[tuple[str, str]] = []

    def load(self, repo_manifest_dirs: list[Path], user_manifest_dirs: list[Path] | None = None) -> None:
        """Load manifests from repository and optional user directories.

        Precedence:
        1. repository native definition
        2. validated user override
        3. legacy adapter
        """
        self.native.clear()
        self.legacy_only.clear()
        self.unsupported.clear()

        for d in repo_manifest_dirs:
            if not d.exists():
                continue
            for path in sorted(d.glob("*.json")):
                try:
                    manifest = load_manifest_file(path)
                except ServiceConfigError as e:
                    self.unsupported.append((path.name, str(e)))
                    continue
                name = manifest["name"]
                if name in self.native:
                    raise ServiceConfigError(f"Duplicate native service name: {name}")
                self.native[name] = manifest

        if user_manifest_dirs:
            for d in user_manifest_dirs:
                if not d.exists():
                    continue
                for path in sorted(d.glob("*.json")):
                    try:
                        manifest = load_manifest_file(path)
                    except ServiceConfigError as e:
                        self.unsupported.append((path.name, str(e)))
                        continue
                    name = manifest["name"]
                    # User override must target a known native service.
                    if name not in self.native:
                        self.unsupported.append((name, "User override for unknown service"))
                        continue
                    base = self.native[name]
                    if self._override_broadens_privileges(base, manifest):
                        self.unsupported.append((name, "User override broadens privileges"))
                        continue
                    self.native[name] = manifest

    def _override_broadens_privileges(self, base: dict[str, Any], override: dict[str, Any]) -> bool:
        base_interp = base.get("command", {}).get("interpreter")
        over_interp = override.get("command", {}).get("interpreter")
        if over_interp != base_interp:
            return True
        return False

    def classify(self, legacy_adapter_services: dict[str, dict[str, Any]] | None = None) -> dict[str, str]:
        result: dict[str, str] = {}
        for name in self.native:
            manifest = self.native[name]
            classification = manifest.get("classification", "NATIVE")
            result[name] = classification
        if legacy_adapter_services:
            for name, info in legacy_adapter_services.items():
                if name in result:
                    continue
                result[name] = info.get("classification", "LEGACY_ONLY")
        return result

    def list(self) -> list[str]:
        return sorted(self.native)
