from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from bootstrap.install_release import BootstrapInstallError, install_global_launcher


def _make_runtime(data_root: Path, release_id: str, label: str) -> Path:
    runtime = data_root / "releases" / release_id / "runtime"
    entry = runtime / "bin" / "hive"
    entry.parent.mkdir(parents=True)
    entry.write_text(
        "import json, sys\n"
        f"print(json.dumps({{'release': {label!r}, 'args': sys.argv[1:]}}))\n",
        encoding="utf-8",
    )
    return runtime.resolve()


def _activate(data_root: Path, release_id: str, runtime: Path) -> None:
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


def test_managed_launcher_follows_active_pointer_across_rollback(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    prefix = tmp_path / "prefix"
    first = _make_runtime(data_root, "release-one", "one")
    second = _make_runtime(data_root, "release-two", "two")

    launcher = install_global_launcher(data_root, prefix)

    _activate(data_root, "release-one", first)
    run_one = subprocess.run(
        [str(launcher), "status"], capture_output=True, text=True, check=True, timeout=15
    )
    assert json.loads(run_one.stdout) == {"release": "one", "args": ["status"]}

    # Simulate the activation engine changing/rolling back the active pointer.
    _activate(data_root, "release-two", second)
    run_two = subprocess.run(
        [str(launcher), "boot"], capture_output=True, text=True, check=True, timeout=15
    )
    assert json.loads(run_two.stdout) == {"release": "two", "args": ["boot"]}


def test_managed_launcher_refuses_unrelated_existing_command(tmp_path: Path) -> None:
    prefix = tmp_path / "prefix"
    launcher = prefix / "bin" / "hive"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/sh\necho unrelated\n", encoding="utf-8")

    with pytest.raises(BootstrapInstallError, match="non-Hive"):
        install_global_launcher(tmp_path / "data", prefix)

    assert launcher.read_text(encoding="utf-8") == "#!/bin/sh\necho unrelated\n"


def test_managed_launcher_rejects_tampered_active_runtime_pointer(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    prefix = tmp_path / "prefix"
    runtime = _make_runtime(data_root, "release-one", "one")
    launcher = install_global_launcher(data_root, prefix)

    _activate(data_root, "release-one", runtime)
    pointer = json.loads((data_root / "active.json").read_text(encoding="utf-8"))
    pointer["active_runtime"] = str(tmp_path / "outside")
    (data_root / "active.json").write_text(json.dumps(pointer), encoding="utf-8")

    result = subprocess.run(
        [str(launcher), "status"], capture_output=True, text=True, check=False, timeout=15
    )
    assert result.returncode == 2
    assert "does not match versioned release layout" in result.stderr
