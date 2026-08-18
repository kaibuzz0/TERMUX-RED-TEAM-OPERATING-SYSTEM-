"""Restart policy and crash-loop protection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from services.errors import ServiceRuntimeError


@dataclass
class RestartState:
    attempts: int = 0
    last_attempt: float = 0.0
    first_attempt: float = 0.0
    crash_loop: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "last_attempt": self.last_attempt,
            "first_attempt": self.first_attempt,
            "crash_loop": self.crash_loop,
        }


class RestartPolicy:
    """Evaluate restart decisions with exponential backoff and crash-loop protection."""

    def __init__(self, manifest: dict[str, Any]):
        cfg = manifest.get("restart", {})
        self.policy = cfg.get("policy", "never")
        self.max_attempts = cfg.get("max_attempts", 5)
        self.window_seconds = cfg.get("window_seconds", 300)
        self.initial = cfg.get("backoff_initial_seconds", 2)
        self.max_backoff = cfg.get("backoff_max_seconds", 60)
        self.states: dict[str, RestartState] = {}

    def should_restart(self, name: str, exit_code: int | None, manually_stopped: bool) -> tuple[bool, float]:
        if manually_stopped:
            return False, 0.0
        if self.policy == "never":
            return False, 0.0
        if self.policy == "unless-stopped" and manually_stopped:
            return False, 0.0
        if self.policy == "on-failure" and (exit_code == 0 or exit_code is None):
            return False, 0.0

        state = self.states.setdefault(name, RestartState())
        now = time.time()
        if state.attempts == 0:
            state.first_attempt = now
        # Reset attempts if stable window passed. A zero/negative window
        # disables reset so max_attempts can trigger a crash loop deterministically
        # within the same burst (HRA-015).
        if self.window_seconds > 0 and now - state.first_attempt > self.window_seconds:
            state.attempts = 0
            state.first_attempt = now
            state.crash_loop = False

        state.attempts += 1
        state.last_attempt = now
        if state.attempts > self.max_attempts:
            state.crash_loop = True
            raise ServiceRuntimeError(f"Service {name} entered crash loop")

        delay = min(self.initial * (2 ** (state.attempts - 1)), self.max_backoff)
        return True, delay

    def mark_success(self, name: str) -> None:
        state = self.states.setdefault(name, RestartState())
        state.attempts = 0
        state.crash_loop = False

    def reset(self, name: str) -> None:
        self.states[name] = RestartState()
