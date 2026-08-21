"""Canonical production payload boundary verification.

Ensures the release engine excludes reference-only and legacy trees from
production release bundles while preserving the canonical runtime.
"""

from __future__ import annotations

from pathlib import Path

from release_engine.manifest import build_release_manifest


def test_canonical_payload_excludes_reference_trees(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()

    # Canonical runtime contents
    (src / "bin").mkdir()
    (src / "bin" / "hive").write_text("#!/bin/sh\necho hive", encoding="utf-8")
    (src / "installer").mkdir()
    (src / "installer" / "activate.py").write_text("print('activate')", encoding="utf-8")
    (src / "hive-canonical.json").write_text('{"project": "Hive OS"}', encoding="utf-8")

    # Reference-only / legacy trees that must NOT enter production bundle
    for legacy in (
        "blueprints/old-plan.md",
        "evidence/historical-releases/notes.txt",
        "Hive Ops DevAI/bin/hivedev",
        "Hive Ops Final/bin/hive-final",
        "Hermes Plugins/install.sh",
    ):
        target = src / Path(legacy)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("legacy", encoding="utf-8")

    paths = {e["path"] for e in build_release_manifest(src)}

    required = {"bin/hive", "installer/activate.py", "hive-canonical.json"}
    for r in required:
        assert r in paths, f"canonical runtime missing: {r}"

    forbidden = {
        "blueprints/old-plan.md",
        "evidence/historical-releases/notes.txt",
        "Hive Ops DevAI/bin/hivedev",
        "Hive Ops Final/bin/hive-final",
        "Hermes Plugins/install.sh",
    }
    for f in forbidden:
        assert f not in paths, f"reference-only path entered production manifest: {f}"
