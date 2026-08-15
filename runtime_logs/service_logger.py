"""Bounded service log capture.

Each supervised service writes stdout/stderr to predictable log files under
the Hive log root.  Logs are rotated automatically by size.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from runtime_logs.errors import LogConfigError
from runtime_logs.permissions import secure_dir, secure_file
from runtime_logs.rotation import RotationPolicy, rotate_if_needed


class ServiceLogger:
    """Manages stdout/stderr file handles and rotation for one service."""

    def __init__(self, service_name: str, log_root: Path, policy: RotationPolicy | None = None):
        self.service_name = service_name
        self.log_root = log_root
        self.policy = policy or RotationPolicy()
        self.service_dir = self.log_root / "services"
        secure_dir(self.service_dir)
        self.stdout_path = self.service_dir / f"{service_name}.log"
        self.stderr_path = self.service_dir / f"{service_name}.err.log"
        self._stdout = None
        self._stderr = None

    def open_handles(self) -> dict[str, Any]:
        """Return file handles for subprocess stdout/stderr.

        Callers should close these when the service stops.
        """
        secure_dir(self.service_dir)
        rotate_if_needed(self.stdout_path, self.policy)
        rotate_if_needed(self.stderr_path, self.policy)
        self._stdout = open(self.stdout_path, "a", encoding="utf-8")
        self._stderr = open(self.stderr_path, "a", encoding="utf-8")
        secure_file(self.stdout_path)
        secure_file(self.stderr_path)
        return {"stdout": self._stdout, "stderr": self._stderr}

    def close(self) -> None:
        if self._stdout is not None:
            try:
                self._stdout.flush()
                self._stdout.close()
            except OSError:
                pass
            self._stdout = None
        if self._stderr is not None:
            try:
                self._stderr.flush()
                self._stderr.close()
            except OSError:
                pass
            self._stderr = None

    def paths(self) -> dict[str, Path]:
        return {"stdout": self.stdout_path, "stderr": self.stderr_path}


class RuntimeLogger:
    """Structured runtime event log for Hive subsystems."""

    def __init__(self, log_root: Path, subsystem: str, policy: RotationPolicy | None = None):
        self.log_root = log_root
        self.subsystem = subsystem
        self.policy = policy or RotationPolicy()
        self.log_dir = self.log_root / "runtime"
        secure_dir(self.log_dir)
        self.path = self.log_dir / f"{subsystem}.log"

    def write(self, event: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        import json
        import time
        from datetime import datetime, timezone
        rotate_if_needed(self.path, self.policy)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "subsystem": self.subsystem,
            "event": event,
            "message": message,
            "metadata": metadata or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        secure_file(self.path)
