"""Dependency resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set

from release_engine.errors import DependencyError
from release_engine.version import ReleaseVersion, parse_release_version


@dataclass(frozen=True)
class PluginDependency:
    plugin_id: str
    min_version: str | None = None
    max_version: str | None = None
    required: bool = True


def resolve_dependencies(
    requested: List[Dict[str, Any]],
    available: Dict[str, Dict[str, Any]],
    hive_version: str,
    sdk_version: str,
) -> List[Dict[str, Any]]:
    """Deterministic dependency planning.

    Does not install or execute anything.
    """
    resolved: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for req in requested:
        dep_id = req.get("plugin_id")
        if not dep_id:
            raise DependencyError("dependency missing plugin_id")
        if dep_id in seen:
            raise DependencyError(f"duplicate dependency: {dep_id}")
        seen.add(dep_id)

        avail = available.get(dep_id)
        if not avail:
            if req.get("required", True):
                raise DependencyError(f"missing required dependency: {dep_id}")
            continue

        version = avail.get("version", "0.0.0")
        min_v = req.get("min_version")
        max_v = req.get("max_version")
        if min_v:
            if parse_release_version(version).compare(parse_release_version(min_v)) < 0:
                raise DependencyError(f"{dep_id} version {version} below minimum {min_v}")
        if max_v:
            if parse_release_version(version).compare(parse_release_version(max_v)) > 0:
                raise DependencyError(f"{dep_id} version {version} above maximum {max_v}")

        required_hive = req.get("minimum_hive_version")
        if required_hive:
            if parse_release_version(hive_version).compare(parse_release_version(required_hive)) < 0:
                raise DependencyError(f"Hive version {hive_version} below {required_hive}")

        required_sdk = req.get("minimum_sdk_version")
        if required_sdk:
            if parse_release_version(sdk_version).compare(parse_release_version(required_sdk)) < 0:
                raise DependencyError(f"SDK version {sdk_version} below {required_sdk}")

        resolved.append({
            "plugin_id": dep_id,
            "resolved_version": version,
            "source": avail.get("source"),
        })

    return resolved


def detect_cycle(graph: Dict[str, List[str]]) -> List[str] | None:
    """Return a cycle if one exists, otherwise None."""
    visited: Set[str] = set()
    stack: Set[str] = set()

    def visit(node: str, path: List[str]) -> List[str] | None:
        if node in stack:
            return path + [node]
        if node in visited:
            return None
        visited.add(node)
        stack.add(node)
        for nxt in graph.get(node, []):
            cycle = visit(nxt, path + [node])
            if cycle:
                return cycle
        stack.discard(node)
        return None

    for node in graph:
        cycle = visit(node, [])
        if cycle:
            return cycle
    return None
