"""CLI surface for `hive service *` commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from services.errors import ServiceConfigError, ServiceRuntimeError
from services.graph import DependencyGraph
from services.legacy import build_migration_plan
from services.registry import ServiceRegistry
from services.schema import validate_manifest
from services.supervisor import Supervisor


def _repo_root() -> Path:
    from lib.hive_path import resolve_repository_root_from_file
    # Anchor repository discovery to this module file location.
    return resolve_repository_root_from_file(__file__)


def _make_registry() -> ServiceRegistry:
    from config_engine import get_config
    svc_cfg = get_config("services")
    repo_root = _repo_root()
    state_root = Path(svc_cfg["state_root"])
    registry = ServiceRegistry(repo_root, state_root)
    repo_manifest_dirs = [Path(d) for d in svc_cfg.get("manifest_dirs", [])]
    user_manifest_dirs = [Path(d) for d in svc_cfg.get("user_override_dirs", [])]
    registry.load(repo_manifest_dirs, user_manifest_dirs)
    return registry


def _make_supervisor() -> Supervisor:
    from config_engine import get_config
    registry = _make_registry()
    svc_cfg = get_config("services")
    state_root = Path(svc_cfg["state_root"])
    log_root = Path(svc_cfg["log_root"])
    return Supervisor(registry.native, state_root, log_root, {})


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_list(args: argparse.Namespace) -> int:
    registry = _make_supervisor().manifests
    _print_json({"services": sorted(registry)})
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    sup = _make_supervisor()
    _print_json(sup.manifests[args.service])
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    registry = _make_supervisor().manifests
    errors = []
    for name in sorted(registry):
        try:
            validate_manifest(registry[name])
        except ServiceConfigError as e:
            errors.append({"service": name, "error": str(e)})
    _print_json({"valid": len(errors) == 0, "errors": errors})
    return 0 if not errors else 2


def cmd_graph(args: argparse.Namespace) -> int:
    sup = _make_supervisor()
    graph = DependencyGraph(sup.manifests)
    _print_json({"order": graph.order()})
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    sup = _make_supervisor()
    _print_json(sup.status(args.service))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    sup = _make_supervisor()
    _print_json(sup.health(args.service))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    sup = _make_supervisor()
    try:
        _print_json(sup.start(args.service))
        return 0
    except ServiceRuntimeError as e:
        print(f"start failed: {e}", file=sys.stderr)
        return 2


def cmd_stop(args: argparse.Namespace) -> int:
    sup = _make_supervisor()
    _print_json(sup.stop(args.service))
    return 0


def cmd_restart(args: argparse.Namespace) -> int:
    sup = _make_supervisor()
    _print_json(sup.restart(args.service))
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    sup = _make_supervisor()
    _print_json(sup.reset(args.service))
    return 0


def cmd_migrate_legacy_plan(args: argparse.Namespace) -> int:
    root = _repo_root()
    legacy_dir = root / "Hive Ops Final" / "original hive os complete" / "etc" / "services"
    plans = []
    if legacy_dir.exists():
        for path in sorted(legacy_dir.glob("*.svc")):
            if path.name.startswith("_"):
                continue
            plans.append(build_migration_plan(path))
    _print_json({"plans": plans})
    return 0


def cmd_legacy_status(args: argparse.Namespace) -> int:
    root = _repo_root()
    legacy_dir = root / "Hive Ops Final" / "original hive os complete" / "etc" / "services"
    files = []
    if legacy_dir.exists():
        for path in sorted(legacy_dir.glob("*.svc")):
            if path.name.startswith("_"):
                continue
            parsed = build_migration_plan(path)
            files.append({"name": parsed["service_name"], "classification": parsed["classification"]})
    _print_json({"legacy_services": files})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive service")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List services")
    show_p = sub.add_parser("show", help="Show manifest")
    show_p.add_argument("service")
    sub.add_parser("validate", help="Validate all manifests")
    sub.add_parser("graph", help="Show dependency order")

    for name in ("status", "health", "start", "stop", "restart", "reset"):
        p = sub.add_parser(name, help=f"{name.capitalize()} a service")
        p.add_argument("service")

    sub.add_parser("migrate-legacy", help="Show legacy migration plan")
    sub.add_parser("legacy-status", help="Show legacy service classifications")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    handlers = {
        "list": cmd_list,
        "show": cmd_show,
        "validate": cmd_validate,
        "graph": cmd_graph,
        "status": cmd_status,
        "health": cmd_health,
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "reset": cmd_reset,
        "migrate-legacy": cmd_migrate_legacy_plan,
        "legacy-status": cmd_legacy_status,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
