from __future__ import annotations

import json
from pathlib import Path

import pytest

from bootstrap import install_release as bootstrap_install
from bootstrap.verify_bundle import BootstrapVerificationError


def _write_active_state(
    data_root: Path,
    *,
    release_id: str = "release-a",
    security_sequence: int = 21,
    include_metadata: bool = True,
) -> dict:
    runtime = (data_root / "releases" / release_id / "runtime").resolve()
    runtime.mkdir(parents=True)
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "active.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_release_id": release_id,
                "active_runtime": str(runtime),
                "previous_release_id": "",
            }
        ),
        encoding="utf-8",
    )

    metadata = {
        "schema_version": 1,
        "release": {
            "release_id": release_id,
            "security_sequence": security_sequence,
        },
        "signing": {
            "algorithm": "Ed25519",
            "key_id": "test",
            "signature": "signed-placeholder",
        },
    }
    record = {
        "schema_version": 1,
        "release_id": release_id,
        "state": "active",
    }
    if include_metadata:
        record["metadata"] = metadata
    (data_root / "releases" / release_id / ".release.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    return metadata


def test_clean_install_security_state_defaults_to_zero(tmp_path: Path) -> None:
    assert bootstrap_install.resolve_current_security_state(tmp_path / "data") == (0, None)


def test_current_state_is_derived_from_active_signed_metadata(tmp_path: Path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    metadata = _write_active_state(data_root, security_sequence=21)
    verified: list[dict] = []

    def fake_verify_metadata(value: dict) -> None:
        verified.append(value)

    monkeypatch.setattr(bootstrap_install, "verify_metadata", fake_verify_metadata)

    assert bootstrap_install.resolve_current_security_state(data_root) == (21, "release-a")
    assert verified == [metadata]


def test_signed_current_state_cannot_be_weakened_by_explicit_override(tmp_path: Path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    _write_active_state(data_root, security_sequence=21)
    monkeypatch.setattr(bootstrap_install, "verify_metadata", lambda _value: None)

    with pytest.raises(bootstrap_install.BootstrapInstallError, match="sequence conflicts"):
        bootstrap_install.resolve_current_security_state(data_root, explicit_sequence=20)

    with pytest.raises(bootstrap_install.BootstrapInstallError, match="release id conflicts"):
        bootstrap_install.resolve_current_security_state(
            data_root,
            explicit_sequence=21,
            explicit_release_id="different-release",
        )


def test_invalid_signed_current_state_fails_closed(tmp_path: Path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    _write_active_state(data_root, security_sequence=21)

    def reject(_value: dict) -> None:
        raise BootstrapVerificationError("bad signature")

    monkeypatch.setattr(bootstrap_install, "verify_metadata", reject)
    with pytest.raises(bootstrap_install.BootstrapInstallError, match="signed metadata is invalid"):
        bootstrap_install.resolve_current_security_state(
            data_root,
            explicit_sequence=21,
            explicit_release_id="release-a",
        )


def test_legacy_active_release_requires_both_explicit_identity_fields(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    _write_active_state(data_root, include_metadata=False)

    with pytest.raises(bootstrap_install.BootstrapInstallError, match="legacy release"):
        bootstrap_install.resolve_current_security_state(data_root)

    with pytest.raises(bootstrap_install.BootstrapInstallError, match="legacy release"):
        bootstrap_install.resolve_current_security_state(data_root, explicit_sequence=7)

    assert bootstrap_install.resolve_current_security_state(
        data_root,
        explicit_sequence=7,
        explicit_release_id="release-a",
    ) == (7, "release-a")


def test_active_runtime_pointer_mismatch_is_rejected(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    _write_active_state(data_root)
    pointer = json.loads((data_root / "active.json").read_text(encoding="utf-8"))
    pointer["active_runtime"] = str(tmp_path / "outside")
    (data_root / "active.json").write_text(json.dumps(pointer), encoding="utf-8")

    with pytest.raises(bootstrap_install.BootstrapInstallError, match="does not match versioned release layout"):
        bootstrap_install.resolve_current_security_state(data_root)
