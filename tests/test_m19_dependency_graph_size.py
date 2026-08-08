"""Milestone 19 — Dependency graph size/depth boundedness audit.

Production dependency graph bounds catalog:
- services.graph.DependencyGraph — NO explicit depth limit, NO explicit service count limit.
- order() uses iterative BFS + Kahn's algorithm; recursion-safe.
- detect_cycles() uses recursive DFS; deep chains may hit Python recursion limit.
- order() raises ServiceDependencyError on missing dependencies or cycles.
- shutdown_order() delegates to order() and reverses.
"""

from __future__ import annotations

import sys

import pytest


# ---------------------------------------------------------------------------
# 1. No explicit depth limit
# ---------------------------------------------------------------------------

class TestDependencyGraphDepthUnbounded:
    def test_order_accepts_deep_chain(self):
        """DependencyGraph.order() accepts arbitrarily deep dependency chains."""
        from services.graph import DependencyGraph
        depth = 500
        manifests = {}
        for i in range(depth):
            name = f"svc-{i:03d}"
            dep = f"svc-{i-1:03d}" if i > 0 else None
            manifests[name] = {"dependencies": [dep] if dep else []}
        graph = DependencyGraph(manifests)
        ordered = graph.order()
        assert len(ordered) == depth
        # Verify topological order: each service appears after its dependency
        for i in range(1, depth):
            dep_name = f"svc-{i-1:03d}"
            svc_name = f"svc-{i:03d}"
            assert ordered.index(dep_name) < ordered.index(svc_name)

    def test_order_iterative_no_recursion_limit(self):
        """order() uses Kahn's algorithm (iterative), not recursion."""
        from services.graph import DependencyGraph
        depth = 2000
        manifests = {}
        for i in range(depth):
            name = f"svc-{i:04d}"
            dep = f"svc-{i-1:04d}" if i > 0 else None
            manifests[name] = {"dependencies": [dep] if dep else []}
        graph = DependencyGraph(manifests)
        # Should not hit recursion limit because order() is iterative
        ordered = graph.order()
        assert len(ordered) == depth


# ---------------------------------------------------------------------------
# 2. No explicit service count limit
# ---------------------------------------------------------------------------

class TestDependencyGraphSizeUnbounded:
    def test_order_accepts_many_services(self):
        """DependencyGraph.order() accepts many services with no explicit count limit."""
        from services.graph import DependencyGraph
        count = 1000
        manifests = {f"svc-{i:04d}": {"dependencies": []} for i in range(count)}
        graph = DependencyGraph(manifests)
        ordered = graph.order()
        assert len(ordered) == count

    def test_order_accepts_dense_graph(self):
        """DependencyGraph.order() handles a dense graph where every service depends on all previous."""
        from services.graph import DependencyGraph
        count = 50
        manifests = {}
        names = [f"svc-{i:02d}" for i in range(count)]
        for i, name in enumerate(names):
            manifests[name] = {"dependencies": names[:i]}
        graph = DependencyGraph(manifests)
        ordered = graph.order()
        assert len(ordered) == count


# ---------------------------------------------------------------------------
# 3. Cycle detection
# ---------------------------------------------------------------------------

class TestDependencyGraphCycleDetection:
    def test_order_raises_on_cycle(self):
        """order() raises ServiceDependencyError when a cycle exists."""
        from services.graph import DependencyGraph
        from services.errors import ServiceDependencyError
        manifests = {
            "a": {"dependencies": ["b"]},
            "b": {"dependencies": ["c"]},
            "c": {"dependencies": ["a"]},
        }
        graph = DependencyGraph(manifests)
        with pytest.raises(ServiceDependencyError, match="cycle"):
            graph.order()

    def test_detect_cycles_finds_simple_cycle(self):
        """detect_cycles() returns the cycle path for a simple 3-node cycle."""
        from services.graph import DependencyGraph
        manifests = {
            "a": {"dependencies": ["b"]},
            "b": {"dependencies": ["c"]},
            "c": {"dependencies": ["a"]},
        }
        graph = DependencyGraph(manifests)
        cycles = graph.detect_cycles()
        assert len(cycles) >= 1
        cycle = cycles[0]
        assert "a" in cycle
        assert "b" in cycle
        assert "c" in cycle

    def test_detect_cycles_returns_empty_for_acyclic(self):
        """detect_cycles() returns empty list for an acyclic graph."""
        from services.graph import DependencyGraph
        manifests = {
            "a": {"dependencies": ["b"]},
            "b": {"dependencies": ["c"]},
            "c": {"dependencies": []},
        }
        graph = DependencyGraph(manifests)
        cycles = graph.detect_cycles()
        assert cycles == []

    def test_self_dependency_cycle(self):
        """A service depending on itself is detected as a cycle."""
        from services.graph import DependencyGraph
        from services.errors import ServiceDependencyError
        manifests = {
            "a": {"dependencies": ["a"]},
        }
        graph = DependencyGraph(manifests)
        with pytest.raises(ServiceDependencyError, match="cycle"):
            graph.order()


# ---------------------------------------------------------------------------
# 4. Missing dependency detection
# ---------------------------------------------------------------------------

class TestDependencyGraphMissingDependency:
    def test_order_raises_on_missing_dependency(self):
        """order() raises ServiceDependencyError when a dependency does not exist."""
        from services.graph import DependencyGraph
        from services.errors import ServiceDependencyError
        manifests = {
            "a": {"dependencies": ["missing"]},
        }
        graph = DependencyGraph(manifests)
        with pytest.raises(ServiceDependencyError, match="missing service"):
            graph.order()

    def test_order_raises_on_unknown_seed(self):
        """order() raises ServiceDependencyError when a seed service is unknown."""
        from services.graph import DependencyGraph
        from services.errors import ServiceDependencyError
        manifests = {
            "a": {"dependencies": []},
        }
        graph = DependencyGraph(manifests)
        with pytest.raises(ServiceDependencyError, match="Unknown service in seeds"):
            graph.order(seeds=["nonexistent"])


# ---------------------------------------------------------------------------
# 5. shutdown_order reverses order
# ---------------------------------------------------------------------------

class TestShutdownOrder:
    def test_shutdown_order_is_reverse_of_order(self):
        """shutdown_order() returns the reverse of order()."""
        from services.graph import DependencyGraph
        manifests = {
            "a": {"dependencies": ["b"]},
            "b": {"dependencies": ["c"]},
            "c": {"dependencies": []},
        }
        graph = DependencyGraph(manifests)
        startup = graph.order()
        shutdown = graph.shutdown_order(startup)
        assert shutdown == list(reversed(startup))


# ---------------------------------------------------------------------------
# 6. detect_cycles uses recursive DFS
# ---------------------------------------------------------------------------

class TestDetectCyclesRecursion:
    def test_detect_cycles_may_hit_recursion_limit_on_deep_chains(self):
        """detect_cycles() uses recursive DFS; extremely deep chains may hit Python recursion limit."""
        import sys
        from services.graph import DependencyGraph
        depth = sys.getrecursionlimit() + 50
        manifests = {}
        for i in range(depth):
            name = f"svc-{i:05d}"
            dep = f"svc-{i-1:05d}" if i > 0 else None
            manifests[name] = {"dependencies": [dep] if dep else []}
        graph = DependencyGraph(manifests)
        # detect_cycles() uses recursion, so very deep chains may fail
        try:
            cycles = graph.detect_cycles()
            assert cycles == []
        except RecursionError:
            pass  # Expected on extremely deep chains due to recursive DFS


# ---------------------------------------------------------------------------
# 7. Supervisor uses DependencyGraph
# ---------------------------------------------------------------------------

class TestSupervisorUsesGraph:
    def test_supervisor_constructed_with_dependency_graph(self):
        """Supervisor.__init__ constructs a DependencyGraph from manifests."""
        import inspect
        from services.supervisor import Supervisor
        src = inspect.getsource(Supervisor.__init__)
        assert "DependencyGraph" in src

    def test_supervisor_order_delegates_to_graph(self):
        """Supervisor.start ordering delegates to DependencyGraph.order()."""
        import inspect
        from services.supervisor import Supervisor
        src = inspect.getsource(Supervisor)
        assert "graph.order" in src or "self.graph" in src