from __future__ import annotations

import stat
from pathlib import Path

import pytest

from updates.cli import _work_directory
from updates.errors import UpdateError


def test_automatic_workspace_is_private_and_removed() -> None:
    with _work_directory(None, "hive-update-test-") as work:
        captured = work
        assert work.is_dir()
        assert stat.S_IMODE(work.stat().st_mode) == 0o700
        (work / "marker").write_text("ok", encoding="utf-8")
    assert not captured.exists()


def test_explicit_nonempty_workspace_is_rejected_without_deleting_contents(tmp_path: Path) -> None:
    work = tmp_path / "existing"
    work.mkdir()
    marker = work / "keep-me"
    marker.write_text("operator data", encoding="utf-8")

    with pytest.raises(UpdateError, match="must be empty"):
        with _work_directory(str(work), "unused-"):
            pass

    assert marker.read_text(encoding="utf-8") == "operator data"


def test_explicit_file_workspace_is_rejected(tmp_path: Path) -> None:
    work = tmp_path / "not-a-directory"
    work.write_text("operator data", encoding="utf-8")

    with pytest.raises(UpdateError, match="unsafe"):
        with _work_directory(str(work), "unused-"):
            pass

    assert work.read_text(encoding="utf-8") == "operator data"
