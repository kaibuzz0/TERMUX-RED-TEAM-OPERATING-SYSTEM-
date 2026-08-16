"""Reproducible build helpers."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import stat
import tarfile
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List


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
    info.mode = stat.S_IMODE(info.mode)
    return info


@contextmanager
def open_reproducible_tar(output_path: Path) -> Iterator[tarfile.TarFile]:
    """Open a gzip-compressed tar writer with deterministic container metadata.

    ``tarfile.open(..., 'w:gz')`` writes the current time into the gzip header,
    so two otherwise identical release builds can have different SHA-256
    digests.  The release pipeline instead fixes the gzip mtime to zero and
    suppresses the output filename in the gzip header.
    """
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                yield archive


def create_reproducible_tar(
    source_dir: Path,
    output_path: Path,
    manifest: List[Dict[str, Any]],
    metadata: Dict[str, Any],
) -> ReproducibilityClass:
    """Create a deterministic tar archive from an already-canonical manifest."""
    source_dir = source_dir.resolve()
    with open_reproducible_tar(output_path) as tar:
        for entry in manifest:
            full = source_dir / entry["path"]
            if not full.exists():
                continue
            info = tar.gettarinfo(str(full), arcname=entry["path"])
            _normalize_tar_info(info)
            with full.open("rb") as handle:
                tar.addfile(info, handle)
        _add_json(tar, "manifest.json", manifest)
        _add_json(tar, "metadata.json", metadata)
    return ReproducibilityClass.CONTENT_REPRODUCIBLE


def _add_json(tar: tarfile.TarFile, name: str, data: Any) -> None:
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    info = tarfile.TarInfo(name=name)
    info.size = len(raw)
    _normalize_tar_info(info)
    tar.addfile(info, io.BytesIO(raw))


def compute_bundle_digest(path: Path) -> str:
    """SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
