"""Tests for service dependency graph."""

from __future__ import annotations

import pytest

from services.errors import ServiceDependencyError
from services.graph import DependencyGraph


def _manifests():
    return {
        "a": {"name": "a", "dependencies": ["b"]},
        "b": {"name": "b", "dependencies": []},
        "c": {"name": "c", "dependencies": ["a", "b"]},
    }


def test_topological_order():
    graph = DependencyGraph(_manifests())
    order = graph.order()
    assert order.index("b") < order.index("a")
    assert order.index("a") < order.index("c")


def test_cycle_detected():
    manifests = {"x": {"name": "x", "dependencies": ["y"]}, "y": {"name": "y", "dependencies": ["x"]}}
    graph = DependencyGraph(manifests)
    with pytest.raises(ServiceDependencyError):
        graph.order()


def test_missing_dependency():
    manifests = {"a": {"name": "a", "dependencies": ["missing"]}}
    graph = DependencyGraph(manifests)
    with pytest.raises(ServiceDependencyError):
        graph.order()
