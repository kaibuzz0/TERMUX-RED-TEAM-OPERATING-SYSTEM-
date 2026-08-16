from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from bootstrap import install_release as bootstrap_install


def _write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def _mode(path: Path) -> int:
    return os.stat(path).st_mode & 0o7777


def _transaction_fixture(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    prefix = tmp_path / "prefix"
    data_root = tmp_path / "data"
    release_id = "hive-v2-next"
    release_record = data_root / "releases" / release_id / ".release.json"
    active_pointer = data_root / "active.json"
    launcher = prefix / "bin" / "hive"
    bashrc = home / ".bashrc"
    no_autoboot = home / ".config" / "hive" / "no-autoboot"
    backup = bashrc.with_suffix(".bashrc.hive-backup")

    monkeypatch.setenv("HOME", str(home))
    _write(launcher, b"old managed launcher\n", 0o751)
    _write(bashrc, b"old bashrc\n", 0o640)
    _write(no_autoboot, b"disabled\n", 0o600)
    _write(active_pointer, b'{"active_release_id":"hive-v2-old"}\n', 0o640)
    _write(release_record, b'{"release_id":"hive-v2-next","state":"ready_to_activate"}\n', 0o600)

    return {
        "home": home,
        "prefix": prefix,
        "data_root": data_root,
        "release_id": release_id,
        "release_record": release_record,
        "active_pointer": active_pointer,
        "launcher": launcher,
        "bashrc": bashrc,
        "no_autoboot": no_autoboot,
        "backup": backup,
        "ready_runtime": data_root / "releases" / release_id / "runtime",
    }


def test_failed_activation_restores_launcher_autoboot_pointer_and_release_record(tmp_path, monkeypatch):
    paths = _transaction_fixture(tmp_path, monkeypatch)
    before = {
        name: (paths[name].read_bytes(), _mode(paths[name]))
        for name in ("launcher", "bashrc", "no_autoboot", "active_pointer", "release_record")
    }

    def fake_launcher(_data_root: Path, _prefix: Path) -> Path:
        _write(paths["launcher"], b"new launcher\n", 0o755)
        return paths["launcher"]

    def fake_autoboot(_runtime: Path) -> None:
        _write(paths["backup"], b"autoboot backup\n", 0o600)
        _write(paths["bashrc"], b"new managed bashrc\n", 0o600)
        paths["no_autoboot"].unlink()

    class FailingActive:
        def activate(self, release_id: str, approve: bool = False):
            assert release_id == paths["release_id"]
            assert approve is True
            _write(paths["active_pointer"], b'{"active_release_id":"hive-v2-next"}\n', 0o600)
            _write(paths["release_record"], b'{"release_id":"hive-v2-next","state":"active"}\n', 0o644)
            raise RuntimeError("injected pointer-finalization failure")

    monkeypatch.setattr(bootstrap_install, "install_global_launcher", fake_launcher)
    monkeypatch.setattr(bootstrap_install, "enable_termux_autoboot", fake_autoboot)

    with pytest.raises(RuntimeError, match="injected pointer-finalization failure"):
        bootstrap_install.finalize_termux_activation(
            FailingActive(),
            paths["release_id"],
            paths["ready_runtime"],
            data_root=paths["data_root"],
            prefix=paths["prefix"],
        )

    for name, (expected_bytes, expected_mode) in before.items():
        assert paths[name].read_bytes() == expected_bytes
        assert _mode(paths[name]) == expected_mode
    assert not paths["backup"].exists()


def test_failed_autoboot_restores_launcher_and_never_activates(tmp_path, monkeypatch):
    paths = _transaction_fixture(tmp_path, monkeypatch)
    old_launcher = paths["launcher"].read_bytes()
    old_bashrc = paths["bashrc"].read_bytes()
    old_disable = paths["no_autoboot"].read_bytes()
    old_pointer = paths["active_pointer"].read_bytes()

    def fake_launcher(_data_root: Path, _prefix: Path) -> Path:
        _write(paths["launcher"], b"new launcher\n", 0o755)
        return paths["launcher"]

    def failing_autoboot(_runtime: Path) -> None:
        _write(paths["backup"], b"temporary backup\n", 0o600)
        _write(paths["bashrc"], b"partially changed bashrc\n", 0o600)
        paths["no_autoboot"].unlink()
        raise bootstrap_install.BootstrapInstallError("injected autoboot failure")

    class MustNotActivate:
        def activate(self, *_args, **_kwargs):
            raise AssertionError("activation must not run after autoboot failure")

    monkeypatch.setattr(bootstrap_install, "install_global_launcher", fake_launcher)
    monkeypatch.setattr(bootstrap_install, "enable_termux_autoboot", failing_autoboot)

    with pytest.raises(bootstrap_install.BootstrapInstallError, match="injected autoboot failure"):
        bootstrap_install.finalize_termux_activation(
            MustNotActivate(),
            paths["release_id"],
            paths["ready_runtime"],
            data_root=paths["data_root"],
            prefix=paths["prefix"],
        )

    assert paths["launcher"].read_bytes() == old_launcher
    assert paths["bashrc"].read_bytes() == old_bashrc
    assert paths["no_autoboot"].read_bytes() == old_disable
    assert paths["active_pointer"].read_bytes() == old_pointer
    assert not paths["backup"].exists()


def test_successful_finalization_commits_mutations(tmp_path, monkeypatch):
    paths = _transaction_fixture(tmp_path, monkeypatch)

    def fake_launcher(_data_root: Path, _prefix: Path) -> Path:
        _write(paths["launcher"], b"committed launcher\n", 0o755)
        return paths["launcher"]

    def fake_autoboot(_runtime: Path) -> None:
        _write(paths["bashrc"], b"committed autoboot\n", 0o600)
        paths["no_autoboot"].unlink()

    class SuccessfulActive:
        def activate(self, release_id: str, approve: bool = False):
            _write(paths["active_pointer"], b'{"active_release_id":"hive-v2-next"}\n', 0o600)
            _write(paths["release_record"], b'{"release_id":"hive-v2-next","state":"active"}\n', 0o600)
            return SimpleNamespace(active_runtime=str(paths["ready_runtime"]), previous_release_id="hive-v2-old")

    monkeypatch.setattr(bootstrap_install, "install_global_launcher", fake_launcher)
    monkeypatch.setattr(bootstrap_install, "enable_termux_autoboot", fake_autoboot)

    pointer, launcher = bootstrap_install.finalize_termux_activation(
        SuccessfulActive(),
        paths["release_id"],
        paths["ready_runtime"],
        data_root=paths["data_root"],
        prefix=paths["prefix"],
    )

    assert launcher == paths["launcher"]
    assert pointer.previous_release_id == "hive-v2-old"
    assert paths["launcher"].read_bytes() == b"committed launcher\n"
    assert paths["bashrc"].read_bytes() == b"committed autoboot\n"
    assert not paths["no_autoboot"].exists()
    assert b"hive-v2-next" in paths["active_pointer"].read_bytes()


def test_transaction_rejects_symlinked_mutable_state(tmp_path, monkeypatch):
    paths = _transaction_fixture(tmp_path, monkeypatch)
    target = tmp_path / "outside-bashrc"
    target.write_text("outside\n", encoding="utf-8")
    paths["bashrc"].unlink()
    paths["bashrc"].symlink_to(target)

    with pytest.raises(bootstrap_install.BootstrapInstallError, match="symlink"):
        bootstrap_install.finalize_termux_activation(
            object(),
            paths["release_id"],
            paths["ready_runtime"],
            data_root=paths["data_root"],
            prefix=paths["prefix"],
        )
    assert target.read_text(encoding="utf-8") == "outside\n"
