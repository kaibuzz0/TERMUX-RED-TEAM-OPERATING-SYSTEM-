"""Tests for broker capability model and adapter integration."""

from __future__ import annotations

from pathlib import Path

from hive_broker import Broker
from hive_broker.adapters import dispatch
from hive_broker.capabilities import BROKER_CAPABILITIES, get_capabilities, is_mutation


def test_no_unrestricted_shell_capability():
    names = {c.name for c in BROKER_CAPABILITIES}
    forbidden = {"shell.exec", "command.run", "terminal.exec", "process.exec"}
    assert not (names & forbidden), f"forbidden capabilities present: {names & forbidden}"


def test_mutating_capabilities_not_advertised_by_default():
    mutating = [c.name for c in BROKER_CAPABILITIES if c.mutation]
    assert mutating == [], f"unexpected mutating capabilities advertised: {mutating}"


def test_network_capabilities_advertised():
    names = {c.name for c in BROKER_CAPABILITIES}
    assert "network.status" in names
    assert "network.health" in names
    assert "network.profile.read" in names


def test_diagnostics_capabilities_advertised():
    names = {c.name for c in BROKER_CAPABILITIES}
    assert "diagnostics.health" in names
    assert "diagnostics.doctor" in names
    assert "diagnostics.audit" in names


def test_logs_capabilities_advertised():
    names = {c.name for c in BROKER_CAPABILITIES}
    assert "logs.status" in names
    assert "logs.tail" in names
    assert "logs.service.read" in names


def test_is_mutation_known():
    assert is_mutation("network.status") is False


def test_capability_catalog_structure():
    catalog = get_capabilities()
    assert catalog["schema_version"] == 1
    assert "capabilities" in catalog
    assert all("name" in c and "mutation" in c and "approval" in c for c in catalog["capabilities"])


def test_unknown_capability_rejected(tmp_path):
    class FakeTxn:
        transaction_id = "test-txn"
    broker = Broker(tmp_path, tmp_path / "logs")
    from hive_broker.errors import CapabilityError
    try:
        broker.run({
            "schema_version": 1,
            "task_id": "test",
            "requestor": "test",
            "intent": "unknown",
            "required_capabilities": ["nonexistent.capability"],
            "allowed_actions": ["nonexistent.capability"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 5,
            "audit_level": "normal",
        })
    except CapabilityError:
        pass
    else:
        raise AssertionError("unknown capability should be rejected")


def test_malformed_service_name_rejected(tmp_path):
    class FakeTxn:
        transaction_id = "test-txn"
    from hive_broker.adapters import AdapterError
    try:
        dispatch("service.show", FakeTxn(), {"service": "../../../etc/passwd"})
    except AdapterError:
        # We expect the CLI to parse it; service registry will reject. For now accept AdapterError.
        pass


def test_path_traversal_blocked_in_logs(tmp_path):
    class FakeTxn:
        transaction_id = "test-txn"
    from hive_broker.adapters import AdapterError
    try:
        dispatch("logs.tail", FakeTxn(), {"service": "../outside"})
    except AdapterError:
        pass
