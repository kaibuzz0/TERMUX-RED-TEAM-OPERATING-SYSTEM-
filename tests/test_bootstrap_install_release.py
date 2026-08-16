from __future__ import annotations

import io
import json
import os
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
    executable_payload = b"#!/usr/bin/env python3\nprint('hive')\n"
    data_payload = b"operator data\n"
    executable = verified / "bin" / "hive"
    executable.parent.mkdir()
    executable.write_bytes(executable_payload)
    data_file = verified / "etc" / "defaults.txt"
    data_file.parent.mkdir()
    data_file.write_bytes(data_payload)

    executable.chmod(0o777)
    data_file.chmod(0o777)

    manifest = [
        {
            "path": "bin/hive",
            "size": len(executable_payload),
            "sha256": "ignored-here-because-bootstrap-already-verified",
            "executable": True,
            "type": "required",
        },
        {
            "path": "etc/defaults.txt",
            "size": len(data_payload),
            "sha256": "ignored-here-because-bootstrap-already-verified",
            "executable": False,
            "type": "required",
        },
    ]
    (verified / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (verified / "metadata.json").write_text(
        json.dumps({"release": {"release_id": "hive-test"}}), encoding="utf-8"
    )

    staged = bootstrap_install.stage_verified_release(verified, tmp_path / "staged")
    staged_executable = staged / "data" / "runtime" / "bin" / "hive"
    staged_data = staged / "data" / "runtime" / "etc" / "defaults.txt"
    assert staged_executable.read_bytes() == executable_payload
    assert staged_data.read_bytes() == data_payload
    assert os.stat(staged_executable).st_mode & 0o777 == 0o700
    assert os.stat(staged_data).st_mode & 0o777 == 0o600
    assert os.stat(staged / "data" / "runtime").st_mode & 0o777 == 0o700
    assert os.stat(staged / "state" / "manifest.json").st_mode & 0o777 == 0o600
    assert os.stat(staged / "metadata.json").st_mode & 0o777 == 0o600

    recorded = json.loads((staged / "state" / "manifest.json").read_text(encoding="utf-8"))
    assert recorded["manifest"] == manifest


def test_stage_verified_release_rejects_unsafe_manifest_path(tmp_path):
    verified = tmp_path / "verified"
    verified.mkdir()
    (verified / "manifest.json").write_text(
        json.dumps([{"path": "../outside", "executable": False}]), encoding="utf-8"
    )
    (verified / "metadata.json").write_text("{}", encoding="utf-8")
    with pytest.raises(bootstrap_install.BootstrapInstallError, match="unsafe"):
        bootstrap_install.stage_verified_release(verified, tmp_path / "staged")


def test_bootstrap_install_verifies_before_handing_release_to_installer(tmp_path, monkeypatch):
    calls: list[str] = []

    def fake_download(url: str, destination: Path) -> int:
        calls.append("download")
        destination.write_bytes(b"signed-bundle-placeholder")
        return destination.stat().st_size

    def fake_verify(
        bundle: Path,
        destination: Path,
        platform: str,
        architecture: str,
        current_sequence: int,
        current_release_id: str | None = None,
    ):
        calls.append("verify")
        assert bundle.is_file()
        assert platform == "termux"
        assert architecture == "aarch64"
        assert current_sequence == 20
        assert current_release_id == "hive-current"
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
        current_release_id="hive-current",
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
