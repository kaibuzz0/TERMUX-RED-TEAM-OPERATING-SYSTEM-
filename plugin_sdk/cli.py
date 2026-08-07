"""Plugin CLI commands.

Implemented: list, inspect, validate, install --plan, capabilities, status, audit, config.
Not implemented: exec, shell, install-url, trust-all, disable-policy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from plugin_sdk import load_manifest
from plugin_sdk.capabilities import validate_capability_set
from plugin_sdk.compatibility import RuntimeVersions, negotiate_compatibility
from plugin_sdk.errors import PluginError
from plugin_sdk.identity import PluginIdentity
from plugin_sdk.loader import inspect_bundle, stage_bundle
from plugin_sdk.registry import PluginEntry, PluginRegistry
from plugin_sdk.signing import classify_signature


def _default_broker_caps() -> set[str]:
    from plugin_sdk.capabilities import TYPE_ALLOWED_CAPABILITIES
    return set(TYPE_ALLOWED_CAPABILITIES["client"])


def _format_plugin(entry: PluginEntry) -> Dict[str, Any]:
    sig = classify_signature(entry.manifest)
    return {
        "id": entry.identity.plugin_id,
        "version": entry.identity.plugin_version,
        "state": entry.lifecycle.state,
        "type": entry.manifest["plugin"]["type"],
        "trust_state": sig.trust_state.value,
        "requested_capabilities": entry.manifest["permissions"]["requested_capabilities"],
        "granted_capabilities": entry.metadata.get("granted_capabilities", []),
        "manifest_digest": entry.identity.manifest_digest,
    }


def cmd_list(registry: PluginRegistry, args: argparse.Namespace) -> int:
    entries = registry.list_plugins()
    result = [_format_plugin(e) for e in entries]
    print(json.dumps(result, indent=2))
    return 0


def cmd_inspect(registry: PluginRegistry, args: argparse.Namespace) -> int:
    if args.path:
        p = Path(args.path)
        if p.is_dir():
            p = p / "manifest.json"
        manifest = load_manifest(p)
        print(json.dumps(manifest, indent=2))
        return 0
    entry = registry.get(args.plugin_id)
    print(json.dumps(_format_plugin(entry), indent=2))
    return 0


def cmd_validate(registry: PluginRegistry, args: argparse.Namespace) -> int:
    path = Path(args.path)
    try:
        if path.is_dir():
            manifest = load_manifest(path / "manifest.json")
        else:
            info = inspect_bundle(path)
            if not info["manifest_present"]:
                raise PluginError("bundle missing manifest.json")
            # Re-read manifest via stage to enforce schema.
            stage = stage_bundle(path, path.parent / ".plugin_staging")
            manifest = load_manifest(stage / "manifest.json")
        broker_caps = _default_broker_caps()
        negotiate_compatibility(manifest, broker_caps)
        requested = manifest["permissions"]["requested_capabilities"]
        validate_capability_set(
            requested,
            broker_caps,
            broker_caps,
            manifest["plugin"]["type"],
        )
        sig = classify_signature(manifest)
        print(json.dumps({
            "valid": True,
            "plugin_id": manifest["plugin"]["id"],
            "trust_state": sig.trust_state.value,
            "requested_capabilities": requested,
            "message": "validation succeeded",
        }, indent=2))
        return 0
    except PluginError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2))
        return 1


def cmd_install_plan(registry: PluginRegistry, args: argparse.Namespace) -> int:
    path = Path(args.path)
    try:
        info = inspect_bundle(path)
        stage = stage_bundle(path, path.parent / ".plugin_staging")
        entry = registry.discover(stage)
        registry.validate(entry.identity.plugin_id)
        requested = entry.manifest["permissions"]["requested_capabilities"]
        broker_caps = _default_broker_caps()
        granted = validate_capability_set(requested, broker_caps, broker_caps, entry.manifest["plugin"]["type"])
        entry.metadata["granted_capabilities"] = granted
        sig = classify_signature(entry.manifest)
        plan = {
            "action": "plan",
            "plugin_id": entry.identity.plugin_id,
            "version": entry.identity.plugin_version,
            "stage_path": str(stage),
            "trust_state": sig.trust_state.value,
            "requested_capabilities": requested,
            "granted_capabilities": granted,
            "lifecycle_state": entry.lifecycle.state,
            "auto_enable": False,
            "note": "explicit enable required after review",
        }
        print(json.dumps(plan, indent=2))
        return 0
    except PluginError as exc:
        print(json.dumps({"action": "error", "error": str(exc)}, indent=2))
        return 1


def cmd_capabilities(registry: PluginRegistry, args: argparse.Namespace) -> int:
    entry = registry.get(args.plugin_id)
    print(json.dumps({
        "requested": entry.manifest["permissions"]["requested_capabilities"],
        "granted": entry.metadata.get("granted_capabilities", []),
    }, indent=2))
    return 0


def cmd_status(registry: PluginRegistry, args: argparse.Namespace) -> int:
    entry = registry.get(args.plugin_id)
    print(json.dumps(_format_plugin(entry), indent=2))
    return 0


def cmd_audit(registry: PluginRegistry, args: argparse.Namespace) -> int:
    entry = registry.get(args.plugin_id)
    print(json.dumps({
        "plugin_id": entry.identity.plugin_id,
        "manifest_digest": entry.identity.manifest_digest,
        "installation_id": entry.identity.installation_id,
        "lifecycle": entry.lifecycle.to_dict() if hasattr(entry.lifecycle, "to_dict") else {
            "state": entry.lifecycle.state,
            "failure_count": entry.lifecycle.failure_count,
        },
    }, indent=2))
    return 0


def cmd_config(registry: PluginRegistry, args: argparse.Namespace) -> int:
    entry = registry.get(args.plugin_id)
    from plugin_sdk.configuration import plugin_config_namespace
    ns = plugin_config_namespace(entry.identity.plugin_id)
    print(json.dumps({"plugin_id": entry.identity.plugin_id, "config_namespace": ns}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hive plugin")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="list registered plugins")
    inspect_p = sub.add_parser("inspect", help="inspect plugin manifest")
    inspect_p.add_argument("--path")
    inspect_p.add_argument("plugin_id", nargs="?")

    validate_p = sub.add_parser("validate", help="validate plugin bundle or directory")
    validate_p.add_argument("path")

    install_p = sub.add_parser("install", help="plan plugin installation")
    install_p.add_argument("path")
    install_p.add_argument("--plan", action="store_true", default=True)

    caps_p = sub.add_parser("capabilities", help="show plugin capabilities")
    caps_p.add_argument("plugin_id")

    status_p = sub.add_parser("status", help="show plugin status")
    status_p.add_argument("plugin_id")

    audit_p = sub.add_parser("audit", help="show plugin audit trail metadata")
    audit_p.add_argument("plugin_id")

    config_p = sub.add_parser("config", help="show plugin config namespace")
    config_p.add_argument("plugin_id")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2

    registry = PluginRegistry()
    handlers = {
        "list": cmd_list,
        "inspect": cmd_inspect,
        "validate": cmd_validate,
        "install": cmd_install_plan,
        "capabilities": cmd_capabilities,
        "status": cmd_status,
        "audit": cmd_audit,
        "config": cmd_config,
    }
    return handlers[args.command](registry, args)


if __name__ == "__main__":
    sys.exit(main())
