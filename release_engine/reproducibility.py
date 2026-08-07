"""Reproducible build helpers."""

from __future__ import annotations

import json
import os
import stat
import tarfile
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


class ReproducibilityClass(Enum):
    BIT_REPRODUCIBLE = "bit_reproducible"
    CONTENT_REPRODUCIBLE = "content_reproducible"
    NOT_REPRODUCIBLE = "not_reproducible"


@dataclass
class ReproducibilityReport:
    classification: ReproducibilityClass
    first_digest: str
    second_digest: str
    differences: List[str]
    timestamp_normalized: bool
    permissions_normalized: bool
    file_ordering_deterministic: bool


def _normalize_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    """Normalize tar metadata for reproducibility."""
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    # Keep mode but strip high bits
    info.mode = stat.S_IMODE(info.mode)
    return info


def _sorted_directory_files(source_dir: Path) -> List[Path]:
    files: List[Path] = []
    for root, dirs, names in os.walk(source_dir):
        dirs.sort()
        for name in sorted(names):
            files.append(Path(root) / name)
    return sorted(files)


def create_reproducible_tar(
    source_dir: Path,
    output_path: Path,
    manifest: List[Dict[str, Any]],
    metadata: Dict[str, Any],
) -> ReproducibilityClass:
    """Create a deterministic tar archive."""
    source_dir = source_dir.resolve()
    files = _sorted_directory_files(source_dir)
    with tarfile.open(output_path, "w:gz") as tar:
        for entry in manifest:
            full = source_dir / entry["path"]
            if not full.exists():
                continue
            info = tar.gettarinfo(str(full), arcname=entry["path"])
            _normalize_tar_info(info)
            with full.open("rb") as f:
                tar.addfile(info, f)
        _add_json(tar, "manifest.json", manifest)
        _add_json(tar, "metadata.json", metadata)
    return ReproducibilityClass.CONTENT_REPRODUCIBLE


def _add_json(tar: tarfile.TarFile, name: str, data: Any) -> None:
    import io

    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(raw)
    _normalize_tar_info(info)
    tar.addfile(info, io.BytesIO(raw))


def compute_bundle_digest(path: Path) -> str:
    """SHA-256 digest of a file."""
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
