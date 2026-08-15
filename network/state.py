"""Persistent network state for Hive OS.

State is stored atomically as JSON and uses restrictive POSIX permissions
when available.  No secrets (cookies, tokens) are persisted here.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from network.errors import NetworkStateError
from network.profiles import NetworkProfile, default_profile_config


@dataclass
class NetworkState:
    """Authoritative persisted network state."""

    profile: str = "hold"
    updated_at: str | None = None
    socks_host: str = ""
    socks_port: int = 0
    control_host: str | None = None
    control_port: int | None = None
    managed_tor: bool = False
    listener_available: bool = False
    control_available: bool = False
    bootstrap_state: str = "unknown"
    proxy_test: bool | None = None
    tor_confirmed: bool | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NetworkState":
        # Silently drop unknown keys for forward compatibility.
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in fields})

    @property
    def profile_enum(self) -> NetworkProfile:
        return NetworkProfile.from_name(self.profile)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _secure_dir(path: Path) -> None:
    """Create directory with restrictive permissions; best-effort on Windows."""
    path.mkdir(parents=True, exist_ok=True)
    try:
        # 0o700: owner read/write/execute only
        path.chmod(0o700)
    except (OSError, NotImplementedError):
        pass


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON state with restrictive permissions."""
    _secure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        try:
            os.chmod(tmp, 0o600)
        except (OSError, NotImplementedError):
            pass
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except (OSError, NotImplementedError):
            pass
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def load_state(state_root: Path) -> NetworkState:
    path = state_root / "network.json"
    if not path.exists():
        return NetworkState(profile="hold", updated_at=_now())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise NetworkStateError(f"Corrupt network state {path}: {e}") from e
    if not isinstance(data, dict):
        raise NetworkStateError(f"Network state {path} must contain an object")
    # Ensure profile name is valid; default to hold if corrupt.
    try:
        NetworkProfile.from_name(data.get("profile", "hold"))
    except ValueError:
        data["profile"] = "hold"
        data["last_error"] = "Previously persisted profile was invalid; reset to hold."
    return NetworkState.from_dict(data)


def save_state(state_root: Path, state: NetworkState) -> None:
    path = state_root / "network.json"
    atomic_write_json(path, state.to_dict())


def update_profile(state_root: Path, profile: NetworkProfile, **fields: Any) -> NetworkState:
    """Persist a profile transition atomically."""
    state = load_state(state_root)
    config = default_profile_config(profile)
    state.profile = str(profile)
    state.updated_at = _now()
    state.socks_host = config.socks_host
    state.socks_port = config.socks_port
    state.control_host = config.control_host
    state.control_port = config.control_port
    state.managed_tor = config.managed_tor
    for k, v in fields.items():
        if hasattr(state, k):
            setattr(state, k, v)
    save_state(state_root, state)
    return state
