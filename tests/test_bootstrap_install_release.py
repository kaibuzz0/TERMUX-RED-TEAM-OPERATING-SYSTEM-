from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from bootstrap import install_release as bootstrap_install
from bootstrap import verify_bundle as bootstrap_verify


class _Response:
    def __init__(self, payload: bytes, url: str = "https://releases.example/hive.tar.gz"):
        self._stream = io.BytesIO(payload)
        self._url = url
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


def test_download_bundle_requires_https(tmp_path):
    with pytest.raises(bootstrap_install.BootstrapInstallError, match="https"):
        bootstrap_install.download_bundle("http://example.test/hive.tar.gz", tmp_path / "bundle")


def test_download_bundle_rejects_insecure_redirect(tmp_path):
    def opener(_request, timeout=60):
        assert timeout == 60
        return _Response(b"bundle", url="http://mirror.example/hive.tar.gz")

    destination = tmp_path / "bundle.tar.gz"
    with pytest.raises(bootstrap_install.BootstrapInstallError, match="https"):
        bootstrap_install.download_bundle(
            "https://releases.example/hive.tar.gz",
            destination,
            opener=opener,
        )
    assert not destination.exists()


def test_download_bundle_enforces_streaming_size_limit(tmp_path):
    payload = b"0123456789"

    def opener(_request, timeout=60):
        return _Response(payload)

    with pytest.raises(bootstrap_install.BootstrapInstallError, match="download limit"):
        bootstrap_install.download_bundle(
            "https://releases.example/hive.tar.gz",
            tmp_path / "bundle.tar.gz",
            opener=opener,
            max_bytes=5,
        )


def test_stage_verified_release_builds_existing_installer_layout(tmp_path):
    verified = tmp_path / "verified"
    verified.mkdir()
    payload = b"#!/usr/bin/env python3\nprint('hive')\n"
    artifact = verified / "bin" / "hive"
    artifact.parent.mkdir()
    artifact.write_bytes(payload)
    manifest = [
        {
            "path": "bin/hive",
            "size": len(payload),
            "sha256": "ignored-here-because-bootstrap-already-verified",
            "executable": True,
            "type": "required",
        }
    ]
    (verified / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (verified / "metadata.json").write_text(
        json.dumps({"release": {"release_id": "hive-test"}}), encoding="utf-8"
    )

    staged = bootstrap_install.stage_verified_release(verified, tmp_path / "staged")
    assert (staged / "data" / "runtime" / "bin" / "hive").read_bytes() == payload
    recorded = json.loads((staged / "state" / "manifest.json").read_text(encoding="utf-8"))
    assert recorded["manifest"] == manifest
    assert (staged / "metadata.json").is_file()


def test_bootstrap_install_verifies_before_handing_release_to_installer(tmp_path, monkeypatch):
    calls: list[str] = []

    def fake_download(url: str, destination: Path) -> int:
        calls.append("download")
        destination.write_bytes(b"signed-bundle-placeholder")
        return destination.stat().st_size

    def fake_verify(bundle: Path, destination: Path, platform: str, architecture: str, current_sequence: int):
        calls.append("verify")
        assert bundle.is_file()
        assert platform == "termux"
        assert architecture == "aarch64"
        assert current_sequence == 20
        destination.mkdir()
        return {"verified": True, "release_id": "hive-v2-test", "version": "2.0.0-rc.2"}

    def fake_install(verified_root: Path, *, data_root: Path, state_root: Path, approve: bool):
        calls.append("install")
        assert verified_root.is_dir()
        assert approve is False
        return {"release_id": "hive-v2-test", "state": "ready_to_activate", "activated": False}

    monkeypatch.setattr(bootstrap_install, "download_bundle", fake_download)
    monkeypatch.setattr(bootstrap_install, "verify_bundle", fake_verify)
    monkeypatch.setattr(bootstrap_install, "install_verified_release", fake_install)

    result = bootstrap_install.bootstrap_install(
        "https://releases.example/hive.tar.gz",
        platform="termux",
        architecture="aarch64",
        current_sequence=20,
        data_root=tmp_path / "data",
        state_root=tmp_path / "state",
        approve=False,
    )
    assert calls == ["download", "verify", "install"]
    assert result["verification"]["verified"] is True
    assert result["installation"]["activated"] is False


def test_manifest_closure_rejects_unsigned_extra_file(tmp_path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "hive").write_text("ok", encoding="utf-8")
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("[]", encoding="utf-8")
    (tmp_path / "unsigned.py").write_text("raise SystemExit('bad')", encoding="utf-8")

    with pytest.raises(bootstrap_verify.BootstrapVerificationError, match="unmanifested"):
        bootstrap_verify._verify_manifest_closure(tmp_path, {"bin/hive"})
