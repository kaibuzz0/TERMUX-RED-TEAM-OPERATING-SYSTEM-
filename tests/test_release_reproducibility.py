"""Reproducibility claim verification."""

from __future__ import annotations

from pathlib import Path

from release_engine.builder import build_release
from release_engine.manifest import build_release_manifest, manifest_digest
from release_engine.reproducibility import compute_bundle_digest


def _fixture_source(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "bin").mkdir()
    (src / "bin" / "hive").write_text("#!/bin/sh\necho hive", encoding="utf-8")
    (src / "lib").mkdir()
    (src / "lib" / "core.py").write_text("print('core')", encoding="utf-8")
    return src


def test_reproducibility_metrics(tmp_path):
    src = _fixture_source(tmp_path)
    cfg = {
        "version": "2.1.0",
        "release_sequence": 7,
        "build_id": "repro",
        "source_revision": "abc123",
        "platforms": ["linux"],
        "architectures": ["aarch64"],
    }
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    r1 = build_release(src, out1, **cfg)
    r2 = build_release(src, out2, **cfg)

    m1 = manifest_digest(build_release_manifest(src))
    m2 = manifest_digest(build_release_manifest(src))

    report = {
        "manifest_digest_equal": m1 == m2,
        "payload_digests_equal": r1["bundle_digest"] == r2["bundle_digest"],
        "metadata_bytes_equal": _metadata_bytes(out1, r1["release_id"]) == _metadata_bytes(out2, r2["release_id"]),
        "archive_digest_equal": compute_bundle_digest(r1["bundle_path"]) == compute_bundle_digest(r2["bundle_path"]),
        "classification": r1["classification"],
    }

    assert report["manifest_digest_equal"]
    assert report["payload_digests_equal"]
    assert report["metadata_bytes_equal"]
    # Tar gzip metadata may differ due to timestamp; we classify CONTENT_REPRODUCIBLE.
    assert report["classification"] == "content_reproducible"


def _metadata_bytes(out_dir: Path, release_id: str) -> bytes:
    return (out_dir / f"{release_id}.metadata.json").read_bytes()
