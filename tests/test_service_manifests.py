"""Tests for service manifest validation including network requirements."""

from __future__ import annotations

import pytest

from services.errors import ServiceConfigError
from services.schema import validate_manifest


def _valid():
    return {
        "schema_version": 1,
        "name": "valid",
        "command": {"interpreter": "python", "args": ["server.py"]},
        "network": {"required": True, "profile": "tor"},
        "health_check": {"type": "tcp-local", "host": "127.0.0.1", "port": 8080},
        "restart": {"policy": "on-failure"},
    }


def test_valid_manifest_with_network():
    assert validate_manifest(_valid())["name"] == "valid"


def test_invalid_network_profile():
    m = _valid()
    m["network"] = {"required": True, "profile": "unknown"}
    with pytest.raises(ServiceConfigError):
        validate_manifest(m)


def test_network_required_not_boolean():
    m = _valid()
    m["network"] = {"required": "yes"}
    with pytest.raises(ServiceConfigError):
        validate_manifest(m)


def test_command_arg_with_shell_metacharacter_rejected():
    m = _valid()
    m["command"]["args"] = [";rm -rf /"]
    with pytest.raises(ServiceConfigError):
        validate_manifest(m)


def test_invalid_restart_policy():
    m = _valid()
    m["restart"] = {"policy": "forever"}
    with pytest.raises(ServiceConfigError):
        validate_manifest(m)


def test_http_local_health_allowed():
    m = _valid()
    m["health_check"] = {"type": "http-local", "host": "127.0.0.1", "port": 8080, "path": "/health"}
    assert validate_manifest(m)["health_check"]["type"] == "http-local"


def test_non_loopback_health_rejected():
    m = _valid()
    m["health_check"] = {"type": "tcp-local", "host": "0.0.0.0", "port": 80}
    with pytest.raises(ServiceConfigError):
        validate_manifest(m)
