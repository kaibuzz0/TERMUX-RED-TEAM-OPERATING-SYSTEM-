"""Offline install end-to-end."""

from __future__ import annotations

import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from release_engine.builder import build_release
from release_engine.registry import ReleaseRegistry, ReleaseRecord
from release_engine.signing import sign_release_metadata
from release_engine.verifier import verify_release_bundle
from updates.trust import TrustStore


def _inject_metadata(bundle: Path, metadata: dict, output: Path) -> None:
    import tarfile
    work = output.parent / ".inject"
    work.mkdir(exist_ok=True)
    with tarfile.open(bundle, "r:gz") as tar:
        tar.extractall(work)
    (work / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    with tarfile.open(output, "w:gz") as tar:
        for f in sorted(work.rglob("*"), key=lambda p: str(p.relative_to(work))):
            if f.is_file():
                tar.add(f, arcname=f.relative_to(work).as_posix())


def test_offline_install_end_to_end(tmp_path):
    private = Ed25519PrivateKey.generate()
    pem = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
    trust_path = tmp_path / "trust.pem"
    trust_path.write_text(f"# key_id: k1\n{pem}", encoding="utf-8")
    trust = TrustStore.from_pem_file(trust_path)

    src = tmp_path / "src"
    src.mkdir()
    (src / "runtime.txt").write_text("v1", encoding="utf-8")
    out = tmp_path / "out"

    result = build_release(src, out, "1.0.0", 1, "b1", "rev1", ["linux"], ["aarch64"])
    signed = sign_release_metadata(result["metadata"], private, "k1", result["manifest_digest"])

    signed_bundle = out / "signed.tar.gz"
    _inject_metadata(result["bundle_path"], signed, signed_bundle)

    work = tmp_path / "work"
    verified = verify_release_bundle(signed_bundle, work, trust, current_sequence=0)

    # Stage
    stage = tmp_path / "stage"
    stage.mkdir()
    # Copy verified payload
    import shutil
    for f in (work / "file.txt", work / "runtime.txt") if (work / "file.txt").exists() else []:
        shutil.copy(f, stage / f.name)

    # Register and activate
    registry = ReleaseRegistry(tmp_path / "registry.json")
    record = ReleaseRecord(
        release_id=verified["metadata"]["release"]["release_id"],
        version="1.0.0",
        release_sequence=1,
        channel="stable",
        manifest_digest=result["manifest_digest"],
        bundle_digest=result["bundle_digest"],
        signing_key_id="k1",
    )
    registry.register(record)
    registry.activate(record.release_id, "t1")

    assert registry.get_active().release_id == record.release_id

    # Rollback point exists
    assert len(registry.rollback_eligible()) == 0
    # Register a newer release and activate it to create rollback eligibility
    registry.register(ReleaseRecord("r2", "1.1.0", 2, "stable", "a" * 64, "b" * 64, "k1"))
    registry.activate("r2", "t2")
    assert any(r.release_id == record.release_id for r in registry.rollback_eligible())
