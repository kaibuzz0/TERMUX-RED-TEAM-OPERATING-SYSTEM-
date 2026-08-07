"""Release build exclusion verification."""

from __future__ import annotations

from pathlib import Path

from release_engine.builder import build_release
from release_engine.manifest import build_release_manifest


def test_build_excludes_forbidden_artifacts(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "good.py").write_text("print(1)", encoding="utf-8")

    forbidden = [
        (".git", "config"),
        (".env",),
        ("release.pem",),
        ("vault.json",),
        ("state", "user.json"),
        ("logs", "agent.log"),
        ("audit", "history.json"),
        (".hermes", "memory.json"),
        ("__pycache__", "cache.pyc"),
        (".pytest_cache", "v", "cached"),
        ("tmp", "session.tmp"),
    ]
    for parts in forbidden:
        target = src
        for part in parts[:-1]:
            target = target / part
            target.mkdir(exist_ok=True)
        (target / parts[-1]).write_text("forbidden", encoding="utf-8")

    # Absolute marker
    (src / "marker.txt").write_text("D:/dev/abs-path", encoding="utf-8")

    out = tmp_path / "out"
    build_release(
        src, out, "1.0.0", 1, "b1", "rev1", ["linux"], ["aarch64"]
    )

    paths = {e["path"] for e in build_release_manifest(src, extra_excludes={"state", "tmp", "audit"})}
    assert "good.py" in paths
    for parts in forbidden:
        rel = "/".join(parts)
        assert rel not in paths, f"excluded path present: {rel}"
    assert "vault.json" not in paths
    assert ".env" not in paths
    assert "release.pem" not in paths
    assert ".git/config" not in paths
