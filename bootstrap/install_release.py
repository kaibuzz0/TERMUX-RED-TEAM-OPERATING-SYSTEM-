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
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bootstrap.verify_bundle import BootstrapVerificationError, _safe_relative_path, verify_bundle

DEFAULT_MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024


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
    """Translate a verified release bundle into the existing installer layout.

    Tar header modes are deliberately not preserved: archive metadata is not part
    of the signed manifest. Runtime permissions are derived only from the signed
    ``executable`` flag, and staging directories remain operator-private.
    """
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


def install_verified_release(
    verified_root: Path,
    *,
    data_root: Path,
    state_root: Path,
    approve: bool,
) -> dict[str, Any]:
    """Hand a verified release to Hive's existing activation engine."""
    metadata = json.loads((verified_root / "metadata.json").read_text(encoding="utf-8"))
    release = metadata.get("release", {})
    release_id = release.get("release_id")
    if not isinstance(release_id, str) or not release_id:
        raise BootstrapInstallError("verified release is missing release_id")

    with tempfile.TemporaryDirectory(prefix="hive-stage-") as staging_dir:
        staging_root = stage_verified_release(verified_root, Path(staging_dir) / "staged")

        # This is the trust boundary: no module from verified_root is imported
        # until verify_bundle has completed successfully.
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


def bootstrap_install(
    bundle_url: str,
    *,
    platform: str,
    architecture: str,
    current_sequence: int,
    data_root: Path,
    state_root: Path,
    approve: bool,
) -> dict[str, Any]:
    """Execute the clean-install trust pipeline from download through readiness."""
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
            current_sequence=current_sequence,
        )
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
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hive-bootstrap-install")
    parser.add_argument("--bundle-url", required=True, help="HTTPS URL of a production-signed Hive release bundle")
    parser.add_argument("--platform", default="termux")
    parser.add_argument(
        "--architecture",
        default=os.uname().machine if hasattr(os, "uname") else "aarch64",
    )
    parser.add_argument("--current-sequence", type=int, default=0)
    parser.add_argument("--data-root", type=Path, default=Path.home() / "Hive-Ops" / "data")
    parser.add_argument("--state-root", type=Path, default=Path.home() / "Hive-Ops" / "state")
    parser.add_argument("--approve", action="store_true", help="activate after verification and promotion")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = bootstrap_install(
            args.bundle_url,
            platform=args.platform,
            architecture=args.architecture,
            current_sequence=args.current_sequence,
            data_root=args.data_root.expanduser().resolve(),
            state_root=args.state_root.expanduser().resolve(),
            approve=args.approve,
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
        else:
            print("Release is verified and ready to activate; re-run with --approve to activate it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
