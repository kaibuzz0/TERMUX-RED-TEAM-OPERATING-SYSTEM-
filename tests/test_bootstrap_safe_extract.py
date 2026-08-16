from __future__ import annotations

import io
import os
import tarfile
from pathlib import Path

import pytest

from bootstrap import verify_bundle as bootstrap_verify


def _archive(path: Path, members: list[tuple[str, bytes | None]]) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        for name, payload in members:
            info = tarfile.TarInfo(name)
            if payload is None:
                info.type = tarfile.DIRTYPE
                info.mode = 0o777
                archive.addfile(info)
            else:
                info.size = len(payload)
                info.mode = 0o777
                archive.addfile(info, io.BytesIO(payload))
    return path


def test_safe_extract_requires_empty_destination(tmp_path: Path) -> None:
    bundle = _archive(tmp_path / "bundle.tar.gz", [("file.txt", b"ok")])
    destination = tmp_path / "destination"
    destination.mkdir()
    (destination / "existing.txt").write_text("do not touch", encoding="utf-8")

    with pytest.raises(bootstrap_verify.BootstrapVerificationError, match="must be empty"):
        bootstrap_verify.safe_extract(bundle, destination)
    assert (destination / "existing.txt").read_text(encoding="utf-8") == "do not touch"


def test_safe_extract_rejects_symlink_destination(tmp_path: Path) -> None:
    bundle = _archive(tmp_path / "bundle.tar.gz", [("file.txt", b"ok")])
    actual = tmp_path / "actual"
    actual.mkdir()
    destination = tmp_path / "destination"
    destination.symlink_to(actual, target_is_directory=True)

    with pytest.raises(bootstrap_verify.BootstrapVerificationError, match="must not be a symlink"):
        bootstrap_verify.safe_extract(bundle, destination)
    assert not (actual / "file.txt").exists()


def test_safe_extract_rejects_regular_file_as_path_prefix(tmp_path: Path) -> None:
    bundle = _archive(
        tmp_path / "conflict.tar.gz",
        [
            ("runtime", b"not-a-directory"),
            ("runtime/bin/hive", b"payload"),
        ],
    )
    with pytest.raises(bootstrap_verify.BootstrapVerificationError, match="path conflicts"):
        bootstrap_verify.safe_extract(bundle, tmp_path / "destination")


def test_safe_extract_enforces_uncompressed_size_limit(tmp_path: Path, monkeypatch) -> None:
    bundle = _archive(tmp_path / "large.tar.gz", [("payload.bin", b"12345")])
    monkeypatch.setattr(bootstrap_verify, "MAX_EXTRACTED_BYTES", 4)

    with pytest.raises(bootstrap_verify.BootstrapVerificationError, match="extraction limit"):
        bootstrap_verify.safe_extract(bundle, tmp_path / "destination")
    assert not (tmp_path / "destination" / "payload.bin").exists()


def test_safe_extract_enforces_member_count_limit(tmp_path: Path, monkeypatch) -> None:
    bundle = _archive(
        tmp_path / "many.tar.gz",
        [("one", b"1"), ("two", b"2")],
    )
    monkeypatch.setattr(bootstrap_verify, "MAX_ARCHIVE_MEMBERS", 1)

    with pytest.raises(bootstrap_verify.BootstrapVerificationError, match="too many members"):
        bootstrap_verify.safe_extract(bundle, tmp_path / "destination")


def test_safe_extract_ignores_attacker_controlled_tar_modes(tmp_path: Path) -> None:
    bundle = _archive(
        tmp_path / "modes.tar.gz",
        [("runtime", None), ("runtime/file.txt", b"payload")],
    )
    destination = tmp_path / "destination"
    bootstrap_verify.safe_extract(bundle, destination)

    assert os.stat(destination).st_mode & 0o777 == 0o700
    assert os.stat(destination / "runtime").st_mode & 0o777 == 0o700
    assert os.stat(destination / "runtime" / "file.txt").st_mode & 0o777 == 0o600
    assert (destination / "runtime" / "file.txt").read_bytes() == b"payload"
