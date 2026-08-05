"""Dependency graph and topological ordering."""

from __future__ import annotations

from collections import deque
from typing import Any

from services.errors import ServiceDependencyError


class DependencyGraph:
    """Directed dependency graph for services."""

    def __init__(self, manifests: dict[str, dict[str, Any]]):
        self.manifests = manifests

    def order(self, seeds: list[str] | None = None, include_disabled: bool = False) -> list[str]:
        """Return topologically sorted service names.

        If seeds is None, all services are considered.
        """
        all_names = set(self.manifests)
        if seeds is None:
            seeds = sorted(all_names)
        else:
            for name in seeds:
                if name not in all_names:
                    raise ServiceDependencyError(f"Unknown service in seeds: {name}")

        # Build subgraph reachable from seeds.
        reachable: set[str] = set()
        queue = deque(seeds)
        while queue:
            name = queue.popleft()
            if name in reachable:
                continue
            if name not in all_names:
                raise ServiceDependencyError(f"Missing dependency: {name}")
            reachable.add(name)
            for dep in self.manifests[name].get("dependencies", []):
                if dep not in all_names:
                    raise ServiceDependencyError(f"Service {name} depends on missing service {dep}")
                queue.append(dep)

        # Kahn's algorithm.
        in_degree: dict[str, int] = {n: 0 for n in reachable}
        adj: dict[str, list[str]] = {n: [] for n in reachable}
        for name in reachable:
            for dep in self.manifests[name].get("dependencies", []):
                if dep in reachable:
                    adj[dep].append(name)
                    in_degree[name] += 1

        ordered: list[str] = []
        ready = sorted([n for n in reachable if in_degree[n] == 0])
        while ready:
            name = ready.pop(0)
            ordered.append(name)
            for child in sorted(adj[name]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    ready.append(child)
                    ready.sort()

        if len(ordered) != len(reachable):
            raise ServiceDependencyError("Dependency cycle detected")
        return ordered

    def shutdown_order(self, running: list[str]) -> list[str]:
        """Reverse dependency order for shutdown."""
        return list(reversed(self.order(running)))

    def detect_cycles(self) -> list[list[str]]:
        """Return list of cycles if any."""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for dep in self.manifests.get(node, {}).get("dependencies", []):
                if dep not in visited:
                    dfs(dep)
                elif dep in rec_stack:
                    idx = path.index(dep)
                    cycles.append(path[idx:] + [dep])
            path.pop()
            rec_stack.remove(node)

        for name in sorted(self.manifests):
            if name not in visited:
                dfs(name)
        return cycles
