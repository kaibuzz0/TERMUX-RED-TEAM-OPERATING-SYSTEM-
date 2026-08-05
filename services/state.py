"""Service state model and persistence."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.errors import ServiceStateError


@dataclass
class ServiceInstance:
    service_name: str
    state: str = "DEFINED"
    pid: int | None = None
    start_time: str | None = None
    command_digest: str | None = None
    manifest_digest: str | None = None
    session_id: str | None = None
    restart_count: int = 0
    last_exit_code: int | None = None
    last_health_status: str | None = None
    last_error: str | None = None
    start_timestamp: str | None = None
    stop_timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServiceInstance":
        return cls(**{k: data.get(k) for k in [f.name for f in cls.__dataclass_fields__.values()]})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def load_state(state_root: Path) -> dict[str, dict[str, Any]]:
    path = state_root / "services.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ServiceStateError(f"Corrupt state file {path}: {e}") from e
    if not isinstance(data, dict):
        raise ServiceStateError(f"State file {path} must contain an object")
    return data


def save_state(state_root: Path, state: dict[str, dict[str, Any]]) -> None:
    path = state_root / "services.json"
    atomic_write_json(path, state)
