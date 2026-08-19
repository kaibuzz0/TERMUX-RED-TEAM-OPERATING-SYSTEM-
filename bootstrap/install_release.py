#!/usr/bin/env python3
"""Download, verify, stage, and optionally activate a Hive release on clean Termux.

The only release code imported by this module is imported *after* the downloaded
bundle has passed bootstrap.verify_bundle's embedded-root signature, manifest,
and archive-safety checks.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from bootstrap.verify_bundle import (
        BootstrapVerificationError,
        _safe_relative_path,
        verify_bundle,
        verify_metadata,
    )
except ImportError:  # pragma: no cover - exercised by the standalone zipapp test
    from verify_bundle import BootstrapVerificationError, _safe_relative_path, verify_bundle, verify_metadata

DEFAULT_MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
MANAGED_LAUNCHER_MARKER = "# HIVE_OS_V2_MANAGED_LAUNCHER"


class BootstrapInstallError(RuntimeError):
    """The clean-install bootstrap could not safely complete."""


def _require_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise BootstrapInstallError("release bundle URL must use https://")


def download_bundle(
    url: str,
    destination: Path,
    *,
    opener: Callable[..., Any] = urlopen,
    max_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
) -> int:
    """Download one release bundle with HTTPS and bounded-size enforcement."""
    _require_https(url)
    if max_bytes <= 0:
        raise BootstrapInstallError("maximum download size must be positive")

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "Hive-OS-bootstrap/2"})
    total = 0
    try:
        with opener(request, timeout=60) as response:
            final_url = response.geturl()
            _require_https(final_url)
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared = int(content_length)
                except ValueError as exc:
                    raise BootstrapInstallError("invalid Content-Length from release server") from exc
                if declared < 0 or declared > max_bytes:
                    raise BootstrapInstallError("release bundle exceeds bootstrap download limit")

            with destination.open("wb") as handle:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise BootstrapInstallError("release bundle exceeds bootstrap download limit")
                    handle.write(chunk)
    except BootstrapInstallError:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise BootstrapInstallError(f"release download failed: {exc}") from exc

    if total == 0:
        destination.unlink(missing_ok=True)
        raise BootstrapInstallError("release server returned an empty bundle")
    return total


def _read_verified_manifest(verified_root: Path) -> list[dict[str, Any]]:
    try:
        manifest = json.loads((verified_root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapInstallError(f"verified manifest became unreadable: {exc}") from exc
    if not isinstance(manifest, list):
        raise BootstrapInstallError("verified manifest is not a list")
    return manifest


def _private_mkdir(path: Path) -> None:
    path.mkdir(exist_ok=True)
    path.chmod(0o700)


def stage_verified_release(verified_root: Path, staging_root: Path) -> Path:
    """Translate a verified release bundle into the existing installer layout."""
    manifest = _read_verified_manifest(verified_root)
    staging_root.mkdir(parents=True, exist_ok=False)
    staging_root.chmod(0o700)
    data_dir = staging_root / "data"
    _private_mkdir(data_dir)
    runtime_root = data_dir / "runtime"
    _private_mkdir(runtime_root)
    state_root = staging_root / "state"
    _private_mkdir(state_root)

    for entry in manifest:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise BootstrapInstallError("verified manifest contains an invalid entry")
        rel = entry["path"]
        try:
            rel_path = _safe_relative_path(rel)
        except BootstrapVerificationError as exc:
            raise BootstrapInstallError(str(exc)) from exc
        source = verified_root.joinpath(*rel_path.parts)
        destination = runtime_root.joinpath(*rel_path.parts)
        if not source.is_file() or source.is_symlink():
            raise BootstrapInstallError(f"verified release artifact disappeared: {rel}")

        parent = runtime_root
        for part in rel_path.parts[:-1]:
            parent = parent / part
            _private_mkdir(parent)

        shutil.copyfile(source, destination)
        destination.chmod(0o700 if entry.get("executable") is True else 0o600)

    state_manifest = state_root / "manifest.json"
    state_manifest.write_text(json.dumps({"manifest": manifest}, indent=2), encoding="utf-8")
    state_manifest.chmod(0o600)

    metadata_destination = staging_root / "metadata.json"
    shutil.copyfile(verified_root / "metadata.json", metadata_destination)
    metadata_destination.chmod(0o600)
    return staging_root


def _launcher_source(data_root: Path) -> str:
    root_literal = repr(str(data_root.resolve()))
    interpreter = Path(sys.executable).expanduser().resolve()
    interpreter_text = str(interpreter)
    if not interpreter.is_file() or "\n" in interpreter_text or "\r" in interpreter_text:
        raise BootstrapInstallError("cannot determine a safe Python interpreter for the global Hive launcher")
    return f'''#!{interpreter_text}
{MANAGED_LAUNCHER_MARKER}
"""Managed Hive OS V2 launcher. Follows the validated active release pointer."""
import json
import os
import sys
from pathlib import Path

DATA_ROOT = Path({root_literal})


def fail(message):
    print(f"Hive launcher error: {{message}}", file=sys.stderr)
    raise SystemExit(2)


try:
    pointer = json.loads((DATA_ROOT / "active.json").read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    fail(f"cannot read active release pointer: {{exc}}")

release_id = pointer.get("active_release_id")
recorded_runtime = pointer.get("active_runtime")
if not isinstance(release_id, str) or not release_id or not isinstance(recorded_runtime, str):
    fail("active release pointer is invalid")
if "/" in release_id or "\\\\" in release_id or release_id in {{".", ".."}}:
    fail("active release id is unsafe")

runtime = (DATA_ROOT / "releases" / release_id / "runtime").resolve()
try:
    runtime.relative_to(DATA_ROOT.resolve())
except ValueError:
    fail("active runtime escapes Hive data root")
if Path(recorded_runtime).resolve() != runtime:
    fail("active runtime pointer does not match versioned release layout")

entry = runtime / "bin" / "hive"
if not entry.is_file() or entry.is_symlink():
    fail("active Hive entrypoint is missing or unsafe")

os.execv(sys.executable, [sys.executable, str(entry), *sys.argv[1:]])
'''


def install_global_launcher(data_root: Path, prefix: Path) -> Path:
    """Install an atomic managed launcher that follows ``active.json``."""
    prefix = prefix.expanduser().resolve()
    launcher_dir = prefix / "bin"
    launcher_dir.mkdir(parents=True, exist_ok=True)
    launcher = launcher_dir / "hive"

    if launcher.exists() or launcher.is_symlink():
        if launcher.is_symlink() or not launcher.is_file():
            raise BootstrapInstallError(f"refusing to overwrite unsafe global hive path: {launcher}")
        try:
            existing = launcher.read_text(encoding="utf-8")
        except OSError as exc:
            raise BootstrapInstallError(f"cannot inspect existing global hive command: {exc}") from exc
        if MANAGED_LAUNCHER_MARKER not in existing:
            raise BootstrapInstallError(f"refusing to overwrite non-Hive global command: {launcher}")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=launcher_dir,
            prefix=".hive-launcher-",
            delete=False,
        ) as handle:
            handle.write(_launcher_source(data_root))
            temp_path = Path(handle.name)
        temp_path.chmod(0o755)
        os.replace(temp_path, launcher)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return launcher


def enable_termux_autoboot(active_runtime: Path) -> None:
    """Enable autoboot using code from the already verified release runtime."""
    manager = active_runtime / "installer" / "autoboot.py"
    if not manager.is_file() or manager.is_symlink():
        raise BootstrapInstallError("verified release is missing a safe installer/autoboot.py")
    try:
        subprocess.run(
            [sys.executable, str(manager), "enable", "--install-dir", str(active_runtime)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootstrapInstallError(f"failed to enable Termux autoboot: {exc}") from exc


def _windows_acl_support_available() -> bool:
    """Return True when running on Windows and ctypes can access ADVAPI32."""
    return sys.platform == "win32"


def _snapshot_windows_acl(path: Path) -> bytes | None:
    """Return the binary SECURITY_DESCRIPTOR for a file, or None on failure."""
    import ctypes
    from ctypes import wintypes
    from ctypes import POINTER

    if not path.exists():
        return None
    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32

    GENERIC_READ = 0x80000000
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    OPEN_EXISTING = 3

    hFile = kernel32.CreateFileW(
        ctypes.c_wchar_p(str(path)),
        GENERIC_READ,
        0,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if hFile == -1:
        return None

    try:
        advapi32.GetSecurityInfo.restype = wintypes.DWORD
        advapi32.GetSecurityInfo.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        pSD = ctypes.c_void_p()
        rc = advapi32.GetSecurityInfo(hFile, 1, 0x00000005, None, None, None, None, ctypes.byref(pSD))
        if rc != 0:
            return None
        advapi32.MakeSelfRelativeSD.restype = wintypes.BOOL
        advapi32.MakeSelfRelativeSD.argtypes = [ctypes.c_void_p, ctypes.c_void_p, POINTER(wintypes.DWORD)]
        advapi32.GetSecurityDescriptorLength.argtypes = [ctypes.c_void_p]
        advapi32.GetSecurityDescriptorLength.restype = wintypes.DWORD
        length = advapi32.GetSecurityDescriptorLength(pSD)
        buf = ctypes.create_string_buffer(length)
        needed = wintypes.DWORD()
        if not advapi32.MakeSelfRelativeSD(pSD, buf, ctypes.byref(needed)):
            return None
        return buf.raw
    finally:
        kernel32.CloseHandle(hFile)


def _restore_windows_acl(path: Path, sddl: bytes | None) -> None:
    """Apply a previously captured SECURITY_DESCRIPTOR to a file."""
    if sddl is None:
        return
    import ctypes
    from ctypes import wintypes
    from ctypes import POINTER

    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32

    GENERIC_WRITE = 0x40000000
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    OPEN_EXISTING = 3

    hFile = kernel32.CreateFileW(
        ctypes.c_wchar_p(str(path)),
        GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if hFile == -1:
        return

    try:
        advapi32.SetSecurityInfo.restype = wintypes.DWORD
        advapi32.SetSecurityInfo.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ]
        advapi32.SetSecurityInfo(hFile, 1, 0x00000005, None, None, ctypes.cast(sddl, ctypes.c_void_p), None)
    finally:
        kernel32.CloseHandle(hFile)


def _snapshot_regular_file(path: Path) -> dict[str, Any]:
    """Capture exact file bytes/mode/ACL without following symlinks."""
    if path.is_symlink():
        raise BootstrapInstallError(f"refusing transactional finalization through symlink: {path}")
    if not path.exists():
        return {"path": path, "existed": False, "data": b"", "mode": 0, "acl": None}
    if not path.is_file():
        raise BootstrapInstallError(f"refusing transactional finalization over non-file path: {path}")
    try:
        snapshot = {
            "path": path,
            "existed": True,
            "data": path.read_bytes(),
            "mode": path.stat().st_mode & 0o7777,
            "acl": _snapshot_windows_acl(path) if _windows_acl_support_available() else None,
        }
        return snapshot
    except OSError as exc:
        raise BootstrapInstallError(f"cannot snapshot finalization state {path}: {exc}") from exc


def _restore_file_snapshot(snapshot: dict[str, Any]) -> None:
    """Atomically restore one snapshot, or remove a file created by the transaction."""
    path = snapshot["path"]
    if not snapshot["existed"]:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.exists():
            raise BootstrapInstallError(f"cannot remove unexpected non-file during rollback: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.rollback-", delete=False) as handle:
            handle.write(snapshot["data"])
            temp_path = Path(handle.name)
        temp_path.chmod(snapshot["mode"])
        if path.exists() and not path.is_file() and not path.is_symlink():
            raise BootstrapInstallError(f"cannot restore file over unexpected non-file: {path}")
        os.replace(temp_path, path)
        temp_path = None
        # os.replace on Windows preserves the destination ACL, so re-apply the
        # intended permission bits after replacement. On platforms where
        # chmod cannot set certain bits (e.g. Windows group/other), this is
        # best-effort and must not abort the rollback.
        try:
            path.chmod(snapshot["mode"])
        except (OSError, NotImplementedError):
            pass
        # Restore captured Windows DACL if available. Best-effort: do not fail
        # the rollback if the platform restricts the operation.
        try:
            _restore_windows_acl(path, snapshot.get("acl"))
        except Exception:
            pass
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _home_for_finalization() -> Path:
    """Return the user's home directory, honoring $HOME first (Termux/Android/CI)."""
    return Path(os.environ.get("HOME", os.path.expanduser("~")))


def _termux_finalization_snapshots(data_root: Path, prefix: Path, release_id: str) -> list[dict[str, Any]]:
    """Snapshot every mutable file touched before activation commits."""
    home = _home_for_finalization()
    bashrc = home / ".bashrc"
    paths = [
        prefix.expanduser().resolve() / "bin" / "hive",
        bashrc,
        bashrc.with_suffix(".bashrc.hive-backup"),
        home / ".config" / "hive" / "no-autoboot",
        data_root / "active.json",
        data_root / "releases" / release_id / ".release.json",
    ]
    return [_snapshot_regular_file(path) for path in paths]


def finalize_termux_activation(
    active: Any,
    release_id: str,
    ready_runtime: Path,
    *,
    data_root: Path,
    prefix: Path,
) -> tuple[Any, Path]:
    """Install Termux integration and activate as one rollback-safe transaction."""
    snapshots = _termux_finalization_snapshots(data_root, prefix, release_id)
    try:
        launcher = install_global_launcher(data_root, prefix)
        enable_termux_autoboot(ready_runtime)
        pointer = active.activate(release_id, approve=True)
        return pointer, launcher
    except Exception as exc:
        rollback_errors: list[str] = []
        for snapshot in reversed(snapshots):
            try:
                _restore_file_snapshot(snapshot)
            except Exception as rollback_exc:  # rollback must attempt every snapshot
                rollback_errors.append(f"{snapshot['path']}: {rollback_exc}")
        if rollback_errors:
            joined = "; ".join(rollback_errors)
            raise BootstrapInstallError(
                f"Termux activation failed ({exc}); finalization rollback was incomplete: {joined}"
            ) from exc
        raise


def install_verified_release(
    verified_root: Path,
    *,
    data_root: Path,
    state_root: Path,
    approve: bool,
    termux_prefix: Path | None = None,
    configure_termux: bool = False,
) -> dict[str, Any]:
    """Hand a verified release to Hive's existing activation engine."""
    metadata = json.loads((verified_root / "metadata.json").read_text(encoding="utf-8"))
    release = metadata.get("release", {})
    release_id = release.get("release_id")
    if not isinstance(release_id, str) or not release_id:
        raise BootstrapInstallError("verified release is missing release_id")
    if configure_termux and termux_prefix is None:
        raise BootstrapInstallError("Termux finalization requires a package PREFIX")

    with tempfile.TemporaryDirectory(prefix="hive-stage-") as staging_dir:
        staging_root = stage_verified_release(verified_root, Path(staging_dir) / "staged")
        sys.path.insert(0, str(verified_root))
        try:
            from installer.activate import ActiveState
            from installer.plan import generate_plan
            from installer.schema import TargetPolicy

            plan = generate_plan(verified_root, transaction_id=release_id)
            plan.target = TargetPolicy(
                root=data_root,
                config_root=state_root / "config",
                state_root=state_root,
                data_root=data_root,
                cache_root=state_root / "cache",
                log_root=state_root / "logs",
                staging_root=state_root / "staging",
            )

            data_root.mkdir(parents=True, exist_ok=True)
            state_root.mkdir(parents=True, exist_ok=True)
            active = ActiveState(data_root=data_root, state_root=state_root, transaction_id=release_id)
            ready = active.promote_to_ready(staging_root.resolve(), plan)
            result: dict[str, Any] = {
                "release_id": release_id,
                "state": ready.state.value,
                "activated": False,
            }
            if approve:
                ready_runtime = (data_root / "releases" / release_id / "runtime").resolve()
                if configure_termux:
                    assert termux_prefix is not None
                    pointer, launcher = finalize_termux_activation(
                        active,
                        release_id,
                        ready_runtime,
                        data_root=data_root,
                        prefix=termux_prefix,
                    )
                    result.update({"global_launcher": str(launcher), "autoboot": "enabled"})
                else:
                    pointer = active.activate(release_id, approve=True)
                result.update(
                    {
                        "state": "active",
                        "activated": True,
                        "active_runtime": pointer.active_runtime,
                        "previous_release_id": pointer.previous_release_id,
                    }
                )
            return result
        finally:
            try:
                sys.path.remove(str(verified_root))
            except ValueError:
                pass


def _termux_prefix(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    value = os.environ.get("PREFIX")
    if not value:
        raise BootstrapInstallError("Termux activation requires PREFIX or --prefix")
    return Path(value).expanduser().resolve()


def resolve_current_security_state(
    data_root: Path,
    *,
    explicit_sequence: int | None = None,
    explicit_release_id: str | None = None,
) -> tuple[int, str | None]:
    """Derive the anti-rollback floor from the active signed release.

    A V2-managed install stores the verified signed metadata in the release
    record. We re-verify that metadata with the embedded production root instead
    of trusting mutable command-line state. Legacy installs that do not have a
    signed metadata record may supply *both* explicit values as a migration
    bridge; malformed/tampered signed metadata is never bypassed by overrides.
    """
    if explicit_sequence is not None and (not isinstance(explicit_sequence, int) or explicit_sequence < 0):
        raise BootstrapInstallError("current security sequence must be a non-negative integer")
    if explicit_release_id is not None and (not isinstance(explicit_release_id, str) or not explicit_release_id):
        raise BootstrapInstallError("current release id must be a non-empty string")

    data_root = data_root.expanduser().resolve()
    pointer_path = data_root / "active.json"
    if not pointer_path.exists():
        if explicit_release_id is not None and explicit_sequence is None:
            raise BootstrapInstallError("--current-release-id requires --current-sequence on a clean/legacy install")
        return explicit_sequence if explicit_sequence is not None else 0, explicit_release_id

    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapInstallError(f"cannot trust corrupt active release pointer: {exc}") from exc
    if not isinstance(pointer, dict) or pointer.get("schema_version") != 1:
        raise BootstrapInstallError("cannot trust active release pointer with unknown schema")

    active_release_id = pointer.get("active_release_id")
    active_runtime = pointer.get("active_runtime")
    if not isinstance(active_release_id, str) or not active_release_id or not isinstance(active_runtime, str):
        raise BootstrapInstallError("active release pointer is invalid")
    if "/" in active_release_id or "\\" in active_release_id or active_release_id in {".", ".."}:
        raise BootstrapInstallError("active release id is unsafe")

    expected_runtime = (data_root / "releases" / active_release_id / "runtime").resolve()
    if Path(active_runtime).expanduser().resolve() != expected_runtime:
        raise BootstrapInstallError("active runtime pointer does not match versioned release layout")

    record_path = data_root / "releases" / active_release_id / ".release.json"
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        record = None
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapInstallError(f"cannot trust corrupt active release record: {exc}") from exc

    if not isinstance(record, dict) or not isinstance(record.get("metadata"), dict):
        if explicit_sequence is None or explicit_release_id is None:
            raise BootstrapInstallError(
                "active legacy release has no signed security state; supply both --current-sequence and --current-release-id"
            )
        if explicit_release_id != active_release_id:
            raise BootstrapInstallError("explicit current release id does not match active release pointer")
        return explicit_sequence, explicit_release_id

    if record.get("release_id") != active_release_id:
        raise BootstrapInstallError("active release record identity does not match active pointer")

    metadata = record["metadata"]
    try:
        verify_metadata(metadata)
    except BootstrapVerificationError as exc:
        raise BootstrapInstallError(f"active release signed metadata is invalid: {exc}") from exc

    release = metadata.get("release")
    if not isinstance(release, dict):
        raise BootstrapInstallError("active signed metadata has no release block")
    signed_release_id = release.get("release_id")
    signed_sequence = release.get("security_sequence")
    if signed_release_id != active_release_id:
        raise BootstrapInstallError("active signed metadata identity does not match active pointer")
    if not isinstance(signed_sequence, int) or isinstance(signed_sequence, bool) or signed_sequence < 0:
        raise BootstrapInstallError("active signed metadata has invalid security sequence")

    if explicit_sequence is not None and explicit_sequence != signed_sequence:
        raise BootstrapInstallError("explicit current sequence conflicts with active signed release")
    if explicit_release_id is not None and explicit_release_id != signed_release_id:
        raise BootstrapInstallError("explicit current release id conflicts with active signed release")
    return signed_sequence, signed_release_id


def bootstrap_install(
    bundle_url: str,
    *,
    platform: str,
    architecture: str,
    data_root: Path,
    state_root: Path,
    approve: bool,
    prefix: Path | None = None,
    current_sequence: int | None = None,
    current_release_id: str | None = None,
) -> dict[str, Any]:
    """Execute the clean-install trust pipeline from download through activation."""
    configure_termux = approve and platform == "termux"
    termux_prefix = _termux_prefix(prefix) if configure_termux else None
    effective_sequence, effective_release_id = resolve_current_security_state(
        data_root,
        explicit_sequence=current_sequence,
        explicit_release_id=current_release_id,
    )

    with tempfile.TemporaryDirectory(prefix="hive-bootstrap-") as work_dir:
        work = Path(work_dir)
        bundle = work / "release.tar.gz"
        verified_root = work / "verified"
        downloaded_bytes = download_bundle(bundle_url, bundle)
        verification = verify_bundle(
            bundle,
            verified_root,
            platform,
            architecture,
            current_sequence=effective_sequence,
            current_release_id=effective_release_id,
        )
        if configure_termux:
            installation = install_verified_release(
                verified_root,
                data_root=data_root,
                state_root=state_root,
                approve=approve,
                termux_prefix=termux_prefix,
                configure_termux=True,
            )
        else:
            installation = install_verified_release(
                verified_root,
                data_root=data_root,
                state_root=state_root,
                approve=approve,
            )
        return {
            "downloaded_bytes": downloaded_bytes,
            "verification": verification,
            "installation": installation,
            "current_security_state": {
                "security_sequence": effective_sequence,
                "release_id": effective_release_id,
            },
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive-bootstrap-install")
    parser.add_argument("--bundle-url", required=True, help="HTTPS URL of a production-signed Hive release bundle")
    parser.add_argument("--platform", default="termux")
    parser.add_argument(
        "--architecture",
        default=os.uname().machine if hasattr(os, "uname") else "aarch64",
    )
    parser.add_argument(
        "--current-sequence",
        type=int,
        default=None,
        help="legacy/manual anti-rollback floor; V2 installs derive this from active signed metadata",
    )
    parser.add_argument(
        "--current-release-id",
        help="legacy/manual release identity bound to --current-sequence; V2 installs derive this automatically",
    )
    parser.add_argument("--data-root", type=Path, default=Path.home() / "Hive-Ops" / "data")
    parser.add_argument("--state-root", type=Path, default=Path.home() / "Hive-Ops" / "state")
    parser.add_argument("--prefix", type=Path, help="Termux package prefix; defaults to $PREFIX")
    parser.add_argument("--approve", action="store_true", help="activate after verification and promotion")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = bootstrap_install(
            args.bundle_url,
            platform=args.platform,
            architecture=args.architecture,
            current_sequence=args.current_sequence,
            current_release_id=args.current_release_id,
            data_root=args.data_root.expanduser().resolve(),
            state_root=args.state_root.expanduser().resolve(),
            approve=args.approve,
            prefix=args.prefix,
        )
    except (BootstrapInstallError, BootstrapVerificationError, OSError, ValueError) as exc:
        print(f"Hive clean-install bootstrap failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
    else:
        verification = result["verification"]
        installation = result["installation"]
        print(f"Verified Hive release: {verification['release_id']} ({verification['version']})")
        if installation["activated"]:
            print(f"Activated runtime: {installation['active_runtime']}")
            if installation.get("global_launcher"):
                print(f"Global command: {installation['global_launcher']}")
            if installation.get("autoboot") == "enabled":
                print("Termux autoboot: enabled")
        else:
            print("Release is verified and ready to activate; re-run with --approve to activate it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
