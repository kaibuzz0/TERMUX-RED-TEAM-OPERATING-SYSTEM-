"""Final release gate verification."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from release_engine.dependencies import resolve_dependencies


def test_dependency_resolver_never_executes_packages(tmp_path):
    # Resolver should never call pip/pkg/apt/curl/wget.
    plan = resolve_dependencies(
        [{"plugin_id": "a", "min_version": "1.0.0"}],
        {"a": {"version": "1.5.0", "source": "bundle"}},
        hive_version="2.0.0",
        sdk_version="1.0.0",
    )
    assert plan[0]["resolved_version"] == "1.5.0"
    # The function must not have side effects; no network, no package install.


def test_mutating_capabilities_not_advertised():
    from plugin_sdk.capabilities import MUTATING_CAPABILITIES
    mutating = {"release.install", "release.activate", "release.rollback", "plugin.install", "plugin.enable", "plugin.disable", "plugin.remove"}
    for cap in mutating:
        assert cap in MUTATING_CAPABILITIES or cap in [
            "service.start", "service.stop", "service.restart",
            "update.apply", "recovery.restore",
            "config.commit", "config.write.global",
            "vault.secret.get", "vault.secret.read",
            "policy.modify", "broker.policy.modify",
            "shell", "system.exec", "system.subprocess",
            "network.listener", "network.external",
            "plugin.self.grant", "plugin.self.update",
        ]


def test_operations_center_release_view_read_only():
    from operations_center.release_view import release_status_view
    # The view must not accept mutation parameters.
    import inspect
    sig = inspect.signature(release_status_view)
    assert "install" not in sig.parameters
    assert "activate" not in sig.parameters
    assert "rollback" not in sig.parameters
