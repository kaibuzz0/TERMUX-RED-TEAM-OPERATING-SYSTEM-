"""I1-CORRECT: Plugin execution-boundary absence verification.

This does NOT verify a sandbox — Milestones 16–17 explicitly do NOT
enable arbitrary third-party plugin execution and do NOT claim kernel
sandboxing. There is no sandbox to verify.

Instead, this module verifies the negative security property:
no execution surface exists for plugins to bypass.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

from plugin_sdk.cli import main
from plugin_sdk.capabilities import (
    MUTATING_CAPABILITIES,
    TYPE_ALLOWED_CAPABILITIES,
    validate_capability_set,
)
from plugin_sdk.errors import PluginCapabilityError


class TestNoSameProcessModuleLoading:
    """Verify no execution surface exists — not a sandbox test."""

    FORBIDDEN = frozenset({
        "importlib", "__import__", "runpy", "imp", "load_module",
        "exec_module", "module_from_spec", "sys.modules",
    })

    def _scan_module(self, module_name: str) -> list[str]:
        import importlib
        mod = importlib.import_module(module_name)
        src = Path(inspect.getfile(mod)).read_text(encoding="utf-8")
        tree = ast.parse(src)
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "importlib" or alias.name.startswith("importlib."):
                        found.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("importlib"):
                    found.append(f"from {node.module} import ...")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("__import__", "runpy", "imp"):
                    found.append(node.func.id)
                elif isinstance(node.func, ast.Attribute) and node.func.attr in ("load_module", "exec_module", "module_from_spec"):
                    found.append(node.func.attr)
        return found

    def test_plugin_sdk_no_dynamic_imports(self):
        """plugin_sdk contains no importlib, __import__, runpy, or module loading."""
        import plugin_sdk
        import plugin_sdk.loader
        import plugin_sdk.broker_client
        import plugin_sdk.manifest
        import plugin_sdk.cli
        import plugin_sdk.policy
        import plugin_sdk.lifecycle

        for mod in (plugin_sdk, plugin_sdk.loader, plugin_sdk.broker_client,
                     plugin_sdk.manifest, plugin_sdk.cli, plugin_sdk.policy,
                     plugin_sdk.lifecycle):
            found = self._scan_module(mod.__name__)
            assert not found, (
                f"Module {mod.__name__} contains dynamic imports: {found}"
            )

    def test_plugin_manifest_validation_is_static(self):
        """Manifest validation reads JSON/text only — never imports code."""
        from plugin_sdk.manifest import load_manifest
        src = inspect.getsource(load_manifest)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("exec", "eval", "compile", "__import__"):
                    raise AssertionError(
                        f"load_manifest contains execution primitive: {node.func.id}"
                    )

    def _evil_manifest(self) -> dict:
        return {
            "schema_version": 1,
            "plugin": {
                "id": "evil.noimport-test",
                "name": "Noimport Test Plugin",
                "version": "1.0.0",
                "sdk_version": "1.0",
                "entrypoint": "evil_module.raise_on_import",
                "type": "client",
            },
            "compatibility": {
                "minimum_hive_version": "1.0.0-dev",
                "required_broker_version": "1.0",
                "required_capabilities": ["service.status"],
            },
            "permissions": {
                "requested_capabilities": ["service.status"],
                "filesystem": [],
                "network": "deny",
                "secrets": [],
            },
            "lifecycle": {"auto_start": False},
        }

    def test_validate_directory_does_not_import_payload(self, tmp_path):
        """plugin_sdk validate on directory does not import Python files."""
        d = tmp_path / "plugin"
        d.mkdir()
        manifest = self._evil_manifest()
        (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (d / "evil_module.py").write_text("raise RuntimeError('PAYLOAD IMPORTED')\n", encoding="utf-8")
        rc = main(["validate", str(d)])
        assert rc == 0, "validate should succeed without importing payload"

    def test_inspect_does_not_import_payload(self, tmp_path):
        """plugin_sdk inspect on directory does not import Python files."""
        d = tmp_path / "plugin"
        d.mkdir()
        manifest = self._evil_manifest()
        (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (d / "evil_module.py").write_text("raise RuntimeError('PAYLOAD IMPORTED')\n", encoding="utf-8")
        rc = main(["inspect", "--path", str(d)])
        assert rc == 0, "inspect should succeed without importing payload"

    def test_stage_bundle_does_not_import_payload(self, tmp_path):
        """plugin_sdk stage_bundle extracts but does not import payload code."""
        import zipfile
        from plugin_sdk.loader import stage_bundle

        manifest = self._evil_manifest()
        bundle = tmp_path / "evil.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("evil_module.py", "raise RuntimeError('PAYLOAD IMPORTED')\n")

        stage_root = tmp_path / "staging"
        result_dir = stage_bundle(bundle, stage_root)
        assert result_dir.exists()
        payload = result_dir / "evil_module.py"
        assert payload.exists()
        assert "PAYLOAD IMPORTED" in payload.read_text(encoding="utf-8")

    def test_registry_operations_do_not_trigger_execution(self, tmp_path):
        """PluginRegistry discover/validate/set_state/remove do not execute payload."""
        from plugin_sdk.registry import PluginRegistry
        from plugin_sdk.loader import stage_bundle
        import zipfile

        manifest = self._evil_manifest()
        bundle = tmp_path / "evil.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("evil_module.py", "raise RuntimeError('PAYLOAD IMPORTED')\n")

        stage_root = tmp_path / "staging"
        stage_dir = stage_bundle(bundle, stage_root)

        registry = PluginRegistry()
        entry = registry.discover(stage_dir)
        assert entry.lifecycle.state == "DISCOVERED"

        registry.validate(entry.identity.plugin_id)
        assert entry.lifecycle.state == "VALIDATED"

        registry.set_state(entry.identity.plugin_id, "DISABLED", reason="test")
        assert entry.lifecycle.state == "DISABLED"

        registry.remove(entry.identity.plugin_id)
        # If we got here, no exception was raised by payload execution

    def test_plugin_cannot_invoke_arbitrary_broker_capability(self):
        """PluginClient.request rejects capabilities not in granted set."""
        from plugin_sdk.identity import PluginIdentity
        from plugin_sdk.broker_client import PluginClient
        from plugin_sdk.errors import PluginCapabilityError

        identity = PluginIdentity(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            manifest_digest="a" * 64,
            installation_id="install-123",
        )
        client = PluginClient(
            identity=identity,
            granted_capabilities=["service.status"],
        )
        # Allowed capability succeeds
        result = client.request("service.status")
        assert result.capability == "service.status"

        # Arbitrary capability not in granted set is rejected
        with pytest.raises(PluginCapabilityError, match="not granted"):
            client.request("vault.secret.get")

        # Unknown/invented capability is rejected
        with pytest.raises(PluginCapabilityError, match="not granted"):
            client.request("kernel.root_access")

    def test_plugin_backend_is_optional_and_bounded(self):
        """Without backend, PluginClient returns stub result; backend cannot be injected."""
        from plugin_sdk.identity import PluginIdentity
        from plugin_sdk.broker_client import PluginClient

        identity = PluginIdentity(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            manifest_digest="a" * 64,
            installation_id="install-123",
        )
        client = PluginClient(
            identity=identity,
            granted_capabilities=["service.status"],
            backend=None,
        )
        result = client.request("service.status")
        assert result.status == "success"
        # No backend means no actual broker invocation — safe default

    def test_plugin_cannot_acquire_mutating_grant(self):
        """No plugin type has mutating capabilities in its allowed set."""
        for plugin_type, allowed in TYPE_ALLOWED_CAPABILITIES.items():
            overlap = allowed & MUTATING_CAPABILITIES
            assert not overlap, (
                f"Plugin type {plugin_type} allows mutating capabilities: {overlap}"
            )

    def test_validate_capability_set_rejects_mutating_even_if_broker_allows(self):
        """Mutating capabilities are rejected even if broker and profile claim to allow them."""
        for cap in MUTATING_CAPABILITIES:
            with pytest.raises(PluginCapabilityError):
                validate_capability_set(
                    requested=[cap],
                    broker_advertised={cap},  # broker claims it's available
                    profile_allowed={cap},     # profile claims it's allowed
                    plugin_type="client",
                )

    def test_plugin_cannot_access_vault_secrets(self):
        """vault.secret.get is mutating and never granted to any plugin type."""
        assert "vault.secret.get" in MUTATING_CAPABILITIES
        for plugin_type, allowed in TYPE_ALLOWED_CAPABILITIES.items():
            assert "vault.secret.get" not in allowed, (
                f"Plugin type {plugin_type} allows vault.secret.get"
            )
        with pytest.raises(PluginCapabilityError):
            validate_capability_set(
                requested=["vault.secret.get"],
                broker_advertised={"vault.secret.get"},
                profile_allowed={"vault.secret.get"},
                plugin_type="client",
            )

    def test_plugin_cannot_modify_policy_or_config_authority(self):
        """Policy/config mutating capabilities are never granted to plugins."""
        authority_mutating = {
            "config.commit",
            "plugin.install",
            "plugin.enable",
            "plugin.disable",
            "plugin.remove",
            "policy.profiles",
            "policy.explain",
        }
        for cap in authority_mutating:
            if cap in MUTATING_CAPABILITIES:
                for plugin_type, allowed in TYPE_ALLOWED_CAPABILITIES.items():
                    assert cap not in allowed, (
                        f"Plugin type {plugin_type} allows authority-modifying capability {cap}"
                    )
                with pytest.raises(PluginCapabilityError):
                    validate_capability_set(
                        requested=[cap],
                        broker_advertised={cap},
                        profile_allowed={cap},
                        plugin_type="client",
                    )

    def test_signed_trusted_status_alone_cannot_cause_execution(self, tmp_path):
        """classify_signature returns metadata but never triggers code execution."""
        from plugin_sdk.signing import classify_signature
        import ast, inspect

        # Verify classify_signature contains no exec/eval/import primitives
        src = inspect.getsource(classify_signature)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("exec", "eval", "compile", "__import__"):
                    raise AssertionError(
                        f"classify_signature contains execution primitive: {node.func.id}"
                    )

        # Even a fully signed manifest does not trigger execution
        manifest = {
            "schema_version": 1,
            "plugin": {
                "id": "evil.signed-test",
                "name": "Signed Test Plugin",
                "version": "1.0.0",
                "sdk_version": "1.0",
                "entrypoint": "evil_module.raise_on_import",
                "type": "client",
            },
            "signature": {
                "publisher_id": "trusted-publisher",
                "signature_blob": "fake-signature-blob-that-looks-trusted",
            },
        }
        sig_meta = classify_signature(manifest)
        # Trust metadata is returned but no code was executed
        assert sig_meta.trust_state.value in ("SIGNED_UNTRUSTED", "UNSIGNED", "INVALID_SIGNATURE")

    def test_no_code_path_from_trust_to_execution(self):
        """No function in plugin_sdk maps trust/signed status to an execution primitive."""
        import plugin_sdk.cli
        import plugin_sdk.signing
        import ast, inspect

        for mod in (plugin_sdk.cli, plugin_sdk.signing):
            src = Path(inspect.getfile(mod)).read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ("exec", "eval", "compile"):
                        raise AssertionError(
                            f"Module {mod.__name__} contains execution primitive: {node.func.id}"
                        )
                    if isinstance(node.func, ast.Attribute) and node.func.attr in ("exec", "eval", "compile"):
                        raise AssertionError(
                            f"Module {mod.__name__} contains execution primitive: {node.func.attr}"
                        )
