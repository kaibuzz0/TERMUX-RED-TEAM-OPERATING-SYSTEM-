"""CLI surface for `hive net *` commands."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from config_engine import get_config
from network.errors import NetworkError
from network.health import summarize_health
from network.manager import NetworkManager
from network.profiles import NetworkProfile


def _repo_root() -> Path:
    from lib.hive_path import resolve_repository_root_from_file
    return resolve_repository_root_from_file(__file__)


def _make_manager() -> NetworkManager:
    runtime = get_config("runtime")
    state_root = Path(runtime["state_root"])
    return NetworkManager(state_root=state_root, repo_root=_repo_root())


def _print_json(data: dict[str, Any]) -> None:
    import json
    print(json.dumps(data, indent=2, default=str))


def cmd_status(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    report = mgr.health(include_proxy_test=args.test, include_tor_confirmation=args.confirm)
    if args.json:
        _print_json(report.to_dict())
    else:
        print("Hive Network")
        print("------------")
        print(summarize_health(report))
    return 0


def cmd_direct(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    state = mgr.select_direct()
    print(f"Profile: {state.profile}")
    return 0


def cmd_orbot(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    state = mgr.select_orbot()
    report = mgr.health()
    print(f"Profile: {state.profile}")
    print(f"Overall: {report.overall}")
    return 0


def cmd_tor(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    try:
        state = mgr.select_tor(timeout=args.timeout)
    except NetworkError as exc:
        print(f"Failed to enter TOR profile: {exc}", file=sys.stderr)
        return 2
    report = mgr.health()
    print(f"Profile: {state.profile}")
    print(f"Overall: {report.overall}")
    return 0


def cmd_hold(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    state = mgr.select_hold()
    print(f"Profile: {state.profile}")
    print("HOLD: Hive proxy execution and network-dependent services are disabled.")
    print("This does NOT disable Android networking.")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    data = mgr.test()
    if args.json:
        _print_json(data)
    else:
        print("Hive Network Test")
        print("-----------------")
        print(f"Profile: {data['profile']}")
        print(f"Overall: {data['overall']}")
        for name, check in data["checks"].items():
            status = "PASS" if check["ok"] else "FAIL"
            print(f"  {name}: {status} ({check['detail']})")
    # Return meaningful exit codes.
    if data["overall"] == "healthy":
        return 0
    if data["overall"] == "degraded":
        return 3
    if data["overall"] == "unavailable":
        return 2
    return 1


def cmd_newnym(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    try:
        result = mgr.newnym(timeout=args.timeout)
    except NetworkError as exc:
        print(f"NEWNYM failed: {exc}", file=sys.stderr)
        return 3
    if result["ok"]:
        print("Tor identity renewed.")
        return 0
    print("Tor did not confirm NEWNYM.", file=sys.stderr)
    return 4


def cmd_run(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    allowed, reason = mgr.can_run_proxy()
    if not allowed:
        print(f"Cannot run command: {reason}", file=sys.stderr)
        return 5
    env = mgr.proxy_env()
    if not args.command:
        print("No command provided after `--`.", file=sys.stderr)
        return 5
    result = subprocess.run(args.command, env=env, check=False)
    return result.returncode


def cmd_orbot_ui(args: argparse.Namespace) -> int:
    mgr = _make_manager()
    from network.orbot import OrbotAdapter, OrbotEndpoints
    from network.profiles import default_profile_config
    cfg = default_profile_config(NetworkProfile.ORBOT)
    adapter = OrbotAdapter(OrbotEndpoints(socks_host=cfg.socks_host, socks_port=cfg.socks_port))
    try:
        result = adapter.launch_ui()
        if result["launched"]:
            print("Orbot UI launch requested.")
            return 0
        print(f"Orbot UI launch failed (returncode {result['returncode']}).", file=sys.stderr)
        return 1
    except NetworkError as exc:
        print(f"Orbot UI launch unavailable: {exc}", file=sys.stderr)
        return 1


def _compat_alias(args: argparse.Namespace, target: str) -> int:
    print(f"Compatibility: `hive net {args.profile}` is now `hive net {target}`.")
    if target == "hold":
        print("HOLD disables Hive proxy execution; it does not disable Android networking.")
    return globals()[f"cmd_{target}"](args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive net")
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = sub.add_parser("status", help="Show network status")
    p_status.add_argument("--json", action="store_true")
    p_status.add_argument("--test", action="store_true", help="Include proxy request test")
    p_status.add_argument("--confirm", action="store_true", help="Include Tor confirmation")
    p_status.set_defaults(func=cmd_status)

    # direct / orbot / tor / hold
    p_direct = sub.add_parser("direct", help="Use normal unproxied networking")
    p_direct.set_defaults(func=cmd_direct)

    p_orbot = sub.add_parser("orbot", help="Use Orbot SOCKS")
    p_orbot.set_defaults(func=cmd_orbot)

    p_tor = sub.add_parser("tor", help="Use Hive-managed local Tor")
    p_tor.add_argument("--timeout", type=float, default=60.0)
    p_tor.set_defaults(func=cmd_tor)

    p_hold = sub.add_parser("hold", help="Disable Hive proxy execution")
    p_hold.set_defaults(func=cmd_hold)

    # compatibility aliases
    for old, new in (("local", "tor"), ("off", "hold")):
        p = sub.add_parser(old, help=f"Compatibility alias for {new}")
        if new == "tor":
            p.add_argument("--timeout", type=float, default=60.0)
        p.set_defaults(func=lambda args, new=new: _compat_alias(args, new), profile=old)

    # test
    p_test = sub.add_parser("test", help="Run layered network test")
    p_test.add_argument("--json", action="store_true")
    p_test.set_defaults(func=cmd_test)

    # newnym
    p_newnym = sub.add_parser("newnym", help="Renew Tor identity (TOR profile only)")
    p_newnym.add_argument("--timeout", type=float, default=10.0)
    p_newnym.set_defaults(func=cmd_newnym)

    # orbot-ui
    p_ui = sub.add_parser("orbot-ui", help="Open Orbot Android UI if available")
    p_ui.set_defaults(func=cmd_orbot_ui)

    # run
    p_run = sub.add_parser("run", help="Run command through current Hive network profile")
    p_run.add_argument("command", nargs=argparse.REMAINDER)
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
