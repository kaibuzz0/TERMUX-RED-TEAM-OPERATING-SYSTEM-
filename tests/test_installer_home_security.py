from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from installer.plan import _make_target_policy
from installer.preflight import run_preflight


def test_preflight_missing_home_never_selects_shared_tmp() -> None:
    with patch.dict(os.environ, {}, clear=True):
        result = run_preflight(repo_root=Path.cwd())

    target = Path(result.environment["target_root"])
    assert "HOME is not set" in result.errors
    assert target.is_absolute()
    assert not str(target).startswith("/tmp")


def test_target_policy_requires_home_instead_of_falling_back_to_tmp() -> None:
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="HOME is required"):
            _make_target_policy(Path.cwd())
