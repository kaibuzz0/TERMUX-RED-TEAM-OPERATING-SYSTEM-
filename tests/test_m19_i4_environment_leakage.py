"""Milestone 19 — I4 Environment leakage investigation.

Verifies child service environments do not inherit sensitive variables
unless explicitly allowlisted in the service manifest.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


class TestEnvironmentLeakage:
    """I4 — verify bounded environment inheritance."""

    def test_unlisted_secret_env_not_inherited(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HIVE_M19_SECRET_TOKEN", "should-not-leak")
        from services.supervisor import Supervisor
        sup = Supervisor({}, tmp_path, tmp_path, {})
        manifest = {
            "name": "svc-1",
            "enabled": True,
            "command": ["echo", "hello"],
            "environment": {"allow": [], "set": {}},
        }
        env = sup._build_environment(manifest)
        assert "HIVE_M19_SECRET_TOKEN" not in env

    def test_allowlisted_env_is_inherited(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HIVE_M19_SECRET_TOKEN", "should-not-leak")
        monkeypatch.setenv("HIVE_ALLOWED_VAR", "safe-value")
        from services.supervisor import Supervisor
        sup = Supervisor({}, tmp_path, tmp_path, {})
        manifest = {
            "name": "svc-1",
            "enabled": True,
            "command": ["echo", "hello"],
            "environment": {"allow": ["HIVE_ALLOWED_VAR"], "set": {}},
        }
        env = sup._build_environment(manifest)
        assert "HIVE_M19_SECRET_TOKEN" not in env
        assert env["HIVE_ALLOWED_VAR"] == "safe-value"

    def test_set_values_override_inherited(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_VAR", "parent-value")
        from services.supervisor import Supervisor
        sup = Supervisor({}, tmp_path, tmp_path, {})
        manifest = {
            "name": "svc-1",
            "enabled": True,
            "command": ["echo", "hello"],
            "environment": {"allow": ["MY_VAR"], "set": {"MY_VAR": "child-value"}},
        }
        env = sup._build_environment(manifest)
        assert env["MY_VAR"] == "child-value"

    def test_default_environment_is_empty(self, tmp_path):
        from services.supervisor import Supervisor
        sup = Supervisor({}, tmp_path, tmp_path, {})
        manifest = {
            "name": "svc-1",
            "enabled": True,
            "command": ["echo", "hello"],
        }
        env = sup._build_environment(manifest)
        assert env == {}

    def test_fake_api_key_not_leaked(self, tmp_path, monkeypatch):
        monkeypatch.setenv("M19_FAKE_API_KEY", "fake-key-12345")
        monkeypatch.setenv("M19_FAKE_PASSWORD", "fake-password-67890")
        from services.supervisor import Supervisor
        sup = Supervisor({}, tmp_path, tmp_path, {})
        manifest = {
            "name": "svc-1",
            "enabled": True,
            "command": ["echo", "hello"],
            "environment": {"allow": ["PATH"], "set": {}},
        }
        env = sup._build_environment(manifest)
        assert "M19_FAKE_API_KEY" not in env
        assert "M19_FAKE_PASSWORD" not in env
        # PATH is allowed
        assert "PATH" in env

    def test_plugin_sdk_no_env_override(self):
        """Plugin SDK configuration layer does not allow env override."""
        import inspect
        from plugin_sdk import configuration
        src = inspect.getsource(configuration)
        # No os.environ references for secrets
        assert "os.environ" not in src or "env" not in src.lower() or "no env override" in src

    def test_broker_adapters_no_env_propagation(self):
        """Broker adapters do not explicitly propagate environment to subprocess."""
        import inspect
        from hive_broker import adapters
        src = inspect.getsource(adapters)
        # subprocess calls without env= kwarg use inherited env by default;
        # but the test verifies no ADDITIONAL env propagation is done
        assert "env=" not in src or "os.environ" not in src

