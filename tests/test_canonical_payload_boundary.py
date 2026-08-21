"""Canonical production payload boundary verification.

Ensures the release engine ships only the explicit canonical runtime
allowlist and rejects unknown top-level directories by default.
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
    (src / "etc").mkdir()
    (src / "etc" / "services.json").write_text('{"version": "1"}', encoding="utf-8")

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

    required = {"bin/hive", "installer/activate.py", "hive-canonical.json", "etc/services.json"}
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


def test_canonical_payload_rejects_unknown_top_level(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()

    # Canonical runtime contents
    (src / "bin").mkdir()
    (src / "bin" / "hive").write_text("#!/bin/sh\necho hive", encoding="utf-8")
    (src / "hive-canonical.json").write_text('{"project": "Hive OS"}', encoding="utf-8")

    # Unknown future top-level directories must be rejected by default
    for unknown in (
        "future-feature-2027/module.py",
        "vendor-tooling/config.yaml",
        "experimental-ai/model.py",
    ):
        target = src / Path(unknown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("unknown", encoding="utf-8")

    # Distribution/documentation/development/optional items must be rejected
    for dist_item in (
        "README.md",
        "docs/index.html",
        "MILESTONE20_REPORT.md",
        "brain-plug/therapist.py",
        "bootstrap/__main__.py",
        "scripts/validate_workflow_pins.py",
        "core/README.md",
        "config/capabilities.json",
        "examples/plugin.py",
        "install.sh",
        "install-termux.sh",
        "update.sh",
        "run-hive.cmd",
        "run-hive.ps1",
        "requirements.txt",
        "requirements-extras.txt",
        "requirements-dev.txt",
    ):
        target = src / Path(dist_item)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("dist", encoding="utf-8")

    paths = {e["path"] for e in build_release_manifest(src)}

    assert "bin/hive" in paths
    assert "hive-canonical.json" in paths

    rejected = {
        "future-feature-2027/module.py",
        "vendor-tooling/config.yaml",
        "experimental-ai/model.py",
        "README.md",
        "docs/index.html",
        "MILESTONE20_REPORT.md",
        "brain-plug/therapist.py",
        "bootstrap/__main__.py",
        "scripts/validate_workflow_pins.py",
        "core/README.md",
        "config/capabilities.json",
        "examples/plugin.py",
        "install.sh",
        "install-termux.sh",
        "update.sh",
        "run-hive.cmd",
        "run-hive.ps1",
        "requirements.txt",
        "requirements-extras.txt",
        "requirements-dev.txt",
    }
    for r in rejected:
        assert r not in paths, f"rejected top-level item entered manifest: {r}"
