"""Offline bundle creation, extraction, and safety validation."""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
import zipfile
from pathlib import Path
from typing import Any

from updates.errors import BundleError


MAX_EXPANDED_SIZE = 512 * 1024 * 1024  # 512 MiB
MAX_FILE_COUNT = 50_000


def create_tar_bundle(source_dir: Path, output_path: Path, manifest: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    """Create a tar bundle containing manifest.json and metadata.json plus artifacts."""
    with tarfile.open(output_path, "w:gz") as tar:
        for entry in manifest:
            tar.add(source_dir / entry["path"], arcname=entry["path"])
        _add_json(tar, "manifest.json", manifest)
        _add_json(tar, "metadata.json", metadata)


def _add_json(tar: tarfile.TarFile, name: str, data: Any) -> None:
    import io
    raw = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(raw)
    tar.addfile(info, io.BytesIO(raw))


def extract_bundle(bundle_path: Path, dest_dir: Path) -> None:
    """Safely extract a tar bundle, rejecting unsafe entries."""
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    if bundle_path.suffix == ".zip":
        _extract_zip(bundle_path, dest_dir)
    else:
        _extract_tar(bundle_path, dest_dir)


def _extract_tar(bundle_path: Path, dest_dir: Path) -> None:
    with tarfile.open(bundle_path, "r:*") as tar:
        _validate_and_extract_members(tar.getmembers(), dest_dir, lambda m: tar.extractfile(m))


def _extract_zip(bundle_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(bundle_path, "r") as z:
        _validate_and_extract_members(z.infolist(), dest_dir, lambda m: z.open(m))


def _safe_name(name: str) -> str:
    """Normalize and validate archive entry names.

    Rejects absolute paths, Windows drive letters, UNC paths, traversal,
    and platform-specific separators.
    """
    if not name:
        raise BundleError("Bundle contains empty path")
    if name.startswith(("/", "\\")):
        raise BundleError(f"Bundle contains absolute path: {name}")
    if name.startswith("//"):
        raise BundleError(f"Bundle contains UNC path: {name}")
    # Reject backslash separators and Windows-specific prefixes before normalization.
    if "\\" in name or ":" in name:
        raise BundleError(f"Bundle contains unsafe path: {name}")
    normalized = name.lstrip("/")
    parts = Path(normalized).parts
    if any(part == ".." for part in parts):
        raise BundleError(f"Bundle contains traversal path: {name}")
    return normalized


def _validate_and_extract_members(members, dest_dir: Path, opener) -> None:
    total_size = 0
    file_count = 0
    validated: list[tuple[Any, str]] = []
    for m in members:
        raw_name = m.name if isinstance(m, tarfile.TarInfo) else m.filename
        name = _safe_name(raw_name)
        # Reject symlinks, hardlinks, devices, FIFOs, and sockets.
        if isinstance(m, tarfile.TarInfo):
            # Use tar type bits; issym/issock may not exist on all Python builds.
            if m.type in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                raise BundleError(f"Bundle contains symlink/hardlink: {name}")
            if m.type in (tarfile.CHRTYPE, tarfile.BLKTYPE):
                raise BundleError(f"Bundle contains device entry: {name}")
            if m.type == tarfile.FIFOTYPE:
                raise BundleError(f"Bundle contains FIFO: {name}")
            if m.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE):
                raise BundleError(f"Bundle contains unsupported entry type: {name}")
        else:
            mode = getattr(m, "external_attr", 0) >> 16
            if mode & 0o120000:
                raise BundleError(f"Bundle contains symlink/hardlink: {name}")
            if mode & 0o070000:
                raise BundleError(f"Bundle contains special file: {name}")
        target = (dest_dir / name).resolve()
        # Ensure resolved target remains inside dest_dir and does not pass through a symlink.
        try:
            target.relative_to(dest_dir.resolve())
        except ValueError:
            raise BundleError(f"Bundle path escapes destination: {name}")
        if any(part == ".." for part in target.parts):
            raise BundleError(f"Bundle path escapes destination: {name}")
        member_size = getattr(m, "size", getattr(m, "file_size", 0))
        total_size += member_size
        if total_size > MAX_EXPANDED_SIZE:
            raise BundleError("Bundle expanded size exceeds safety limit")
        file_count += 1
        if file_count > MAX_FILE_COUNT:
            raise BundleError("Bundle file count exceeds safety limit")
        validated.append((m, name))

    # Second pass: extract after validation
    for m, name in validated:
        target = dest_dir / name
        if name.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        # Do not write through a pre-existing symlink.
        if target.is_symlink() or (target.exists() and target.is_symlink()):
            raise BundleError(f"Refusing to write through pre-existing symlink: {name}")
        data = opener(m)
        if data is None:
            continue
        with target.open("wb") as f:
            for chunk in iter(lambda: data.read(65536), b""):
                f.write(chunk)
        if data.close:
            data.close()