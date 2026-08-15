#!/usr/bin/env python3
"""Hive OS Termux integration self-repair.

Commands:
  hive termux repair   -- inspect and repair Termux integration
  hive termux status   -- show Termux integration state
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from installer.autoboot import (
    _bashrc_path,
    _block_present,
    _install_block,
    _is_enabled,
    _no_autoboot_file,
)


def _repo_root() -> Path:
    env_root = os.environ.get("HIVE_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    script_parent = Path(__file__).resolve().parent.parent
    return script_parent


def _find_global_hive() -> Path | None:
    hive = shutil.which("hive")
    if not hive:
        return None
    return Path(hive)


def _is_managed_launcher(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return "# HIVE_OS_MANAGED_LAUNCHER" in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _ensure_executable(path: Path) -> bool:
    """Set executable bit if supported; return True if successful."""
    if not path.is_file():
        return False
    try:
        current = stat.S_IMODE(path.stat().st_mode)
        if current & 0o111:
            return True
        os.chmod(path, current | 0o111)
        return True
    except (OSError, NotImplementedError, AttributeError):
        return False


def _repo_root_for_bash(repo_root: Path) -> str:
    """Return a path string safe for embedding in a bash script."""
    # On Windows test hosts, use forward slashes so the generated Termux script
    # remains correct when written to the actual Android device.
    return repo_root.as_posix()


def _run_global_hive(args: list[str]) -> bool:
    hive_path = _find_global_hive()
    # On some hosts (Windows tests) shutil.which may not find an extensionless
    # launcher. Fall back to the configured prefix path.
    if hive_path is None:
        prefix_str = os.environ.get("HIVE_PREFIX") or os.environ.get("PREFIX") or "/data/data/com.termux/files/usr"
        candidate = Path(prefix_str) / "bin" / "hive"
        if candidate.is_file():
            hive_path = candidate
    if not hive_path:
        return False
    # If the global launcher is a managed bash wrapper, execute the underlying
    # python invocation directly so the repair check works on Windows test hosts too.
    if hive_path.is_file() and _is_managed_launcher(hive_path):
        try:
            launcher_text = hive_path.read_text(encoding="utf-8")
            for line in launcher_text.splitlines():
                line = line.strip()
                if line.startswith("exec python "):
                    parts = line[len("exec "):].split()
                    # Remove bash variable quoting artifacts if any.
                    quote_chars = chr(34) + chr(39)
                    parts = [p.strip(quote_chars) for p in parts]
                    # Drop bash placeholder "$@" if present; replace with actual args.
                    parts = [p for p in parts if p != "$@"]
                    cmd = parts + args
                    expanded = [os.path.expandvars(p) for p in cmd]
                    env = os.environ.copy()
                    env.setdefault("HIVE_REPO_ROOT", str(_repo_root()))
                    result = subprocess.run(expanded, capture_output=True, text=True, timeout=30, env=env)
                    return result.returncode == 0
        except Exception:
            pass
    try:
        result = subprocess.run(
            [str(hive_path)] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def _run_python_repo_hive(repo_root: Path, args: list[str]) -> bool:
    python = shutil.which("python") or shutil.which("python3")
    if not python:
        return False
    launcher = repo_root / "bin" / "hive"
    if not launcher.is_file():
        return False
    try:
        result = subprocess.run(
            [python, str(launcher)] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


class ComponentResult:
    def __init__(self, name: str, ok: bool, fixed: bool = False, detail: str = ""):
        self.name = name
        self.ok = ok
        self.fixed = fixed
        self.detail = detail


def _inspect(repo_root: Path) -> list[ComponentResult]:
    results: list[ComponentResult] = []

    repo_ok = repo_root.is_dir() and (repo_root / "bin" / "hive").is_file()
    results.append(ComponentResult("Repository", repo_ok, False, str(repo_root) if repo_ok else "missing"))

    python = shutil.which("python") or shutil.which("python3")
    results.append(ComponentResult("Python runtime", python is not None, False, python or "not found"))

    global_hive = _find_global_hive()
    # Fallback to configured prefix for extensionless launchers on Windows tests.
    if global_hive is None:
        prefix_str = os.environ.get("HIVE_PREFIX") or os.environ.get("PREFIX") or "/data/data/com.termux/files/usr"
        candidate = Path(prefix_str) / "bin" / "hive"
        if candidate.is_file():
            global_hive = candidate
    managed = global_hive is not None and _is_managed_launcher(global_hive)
    results.append(
        ComponentResult(
            "Global hive command",
            global_hive is not None and managed,
            False,
            str(global_hive) if global_hive else "not found",
        )
    )

    repo_launcher = repo_root / "bin" / "hive"
    if repo_launcher.is_file():
        try:
            mode = stat.S_IMODE(repo_launcher.stat().st_mode)
            is_exec = bool(mode & 0o111)
        except OSError:
            is_exec = False
    else:
        is_exec = False
    # On platforms without executable-bit semantics (e.g. Windows tests), accept existence.
    if not is_exec and repo_launcher.is_file() and os.name == "nt":
        is_exec = True
    results.append(ComponentResult("Launcher executable", is_exec, False))

    bashrc = _bashrc_path()
    results.append(ComponentResult(".bashrc", bashrc.exists(), False, str(bashrc)))

    block_present = _block_present(bashrc)
    enabled = _is_enabled(bashrc) if block_present else None
    if enabled is True:
        state_detail = "enabled"
    elif enabled is False:
        state_detail = "disabled"
    elif block_present:
        state_detail = "present (state unclear)"
    else:
        state_detail = "missing"
    results.append(ComponentResult("Autoboot block", block_present, False, state_detail))

    no_auto = _no_autoboot_file()
    results.append(
        ComponentResult(
            "Persistent disable file",
            not no_auto.exists(),
            False,
            "exists" if no_auto.exists() else "absent",
        )
    )

    if global_hive and managed:
        boot_ok = _run_global_hive(["boot", "--help"])
        route = "global hive"
    else:
        boot_ok = _run_python_repo_hive(repo_root, ["boot", "--help"])
        route = "python repo launcher"
    results.append(ComponentResult("Boot route", boot_ok, False, route))

    return results


def _print_status(results: list[ComponentResult]) -> None:
    print("Hive OS Termux Integration")
    print("-" * 26)
    width = max(len(r.name) for r in results) + 2
    for r in results:
        status = "OK" if r.ok else "FAILED"
        detail = f" ({r.detail})" if r.detail else ""
        print(f"{r.name + ':':{width}} {status}{detail}")


def cmd_status(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    results = _inspect(repo_root)
    _print_status(results)
    return 0 if all(r.ok for r in results) else 1


def cmd_repair(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    bashrc = _bashrc_path()
    results: list[ComponentResult] = []

    repo_launcher = repo_root / "bin" / "hive"
    exec_fixed = False
    if repo_launcher.is_file():
        try:
            mode = stat.S_IMODE(repo_launcher.stat().st_mode)
            if not (mode & 0o111):
                exec_fixed = _ensure_executable(repo_launcher)
        except OSError:
            pass
    results.append(
        ComponentResult(
            "Launcher executable",
            True,
            exec_fixed,
            "fixed" if exec_fixed else "ok",
        )
    )

    global_hive = _find_global_hive()
    managed = global_hive is not None and _is_managed_launcher(global_hive)
    launcher_fixed = False
    if global_hive is None or not managed:
        prefix_str = os.environ.get("HIVE_PREFIX") or os.environ.get("PREFIX") or "/data/data/com.termux/files/usr"
        prefix = Path(prefix_str)
        launcher_dir = prefix / "bin"
        launcher = launcher_dir / "hive"
        # Do not overwrite an unrelated existing command.
        if launcher.exists() and not _is_managed_launcher(launcher):
            results.append(
                ComponentResult(
                    "Global hive command",
                    False,
                    False,
                    f"unrelated launcher exists at {launcher}",
                )
            )
            launcher_fixed = False
        else:
            try:
                launcher_dir.mkdir(parents=True, exist_ok=True)
                repo_path_bash = _repo_root_for_bash(repo_root)
                launcher.write_text(
                    f"""#!/data/data/com.termux/files/usr/bin/env bash
# HIVE_OS_MANAGED_LAUNCHER
# Hive OS global launcher (auto-generated by hive termux repair)
# Forwards all arguments to the installed Hive OS repository launcher.
export HIVE_REPO_ROOT="{repo_path_bash}"
exec python "${{HIVE_REPO_ROOT}}/bin/hive" "$@"
""",
                    encoding="utf-8",
                )
                _ensure_executable(launcher)
                global_hive = launcher
                managed = True
                launcher_fixed = True
            except OSError:
                launcher_fixed = False
    if not any(r.name == "Global hive command" for r in results):
        results.append(
            ComponentResult(
                "Global hive command",
                global_hive is not None and managed,
                launcher_fixed,
                str(global_hive) if global_hive else "not found",
            )
        )

    block_present = _block_present(bashrc)
    enabled = _is_enabled(bashrc) if block_present else None
    block_fixed = False
    if not block_present or enabled is False:
        try:
            _install_block(bashrc, repo_root)
            block_fixed = True
        except OSError:
            pass
    results.append(
        ComponentResult(
            "Autoboot block",
            _block_present(bashrc),
            block_fixed,
            "fixed" if block_fixed else "ok",
        )
    )

    no_auto = _no_autoboot_file()
    disable_cleared = False
    if no_auto.exists():
        try:
            no_auto.unlink()
            disable_cleared = True
        except OSError:
            pass
    results.append(
        ComponentResult(
            "Persistent disable file",
            not _no_autoboot_file().exists(),
            disable_cleared,
            "cleared" if disable_cleared else "ok",
        )
    )

    if global_hive and managed:
        boot_ok = _run_global_hive(["boot", "--help"])
        route = "global hive"
    else:
        boot_ok = _run_python_repo_hive(repo_root, ["boot", "--help"])
        route = "python repo launcher"
    results.append(ComponentResult("Boot route", boot_ok, False, route))

    _print_status(results)
    if not all(r.ok for r in results):
        print("\nSome components could not be repaired. See details above.", file=sys.stderr)
        return 1
    print("\nRestart Termux to verify automatic startup.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive termux")
    subparsers = parser.add_subparsers(dest="action", required=True)

    repair = subparsers.add_parser("repair", help="inspect and repair Termux integration")
    repair.set_defaults(func=cmd_repair)

    status = subparsers.add_parser("status", help="show Termux integration state")
    status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))