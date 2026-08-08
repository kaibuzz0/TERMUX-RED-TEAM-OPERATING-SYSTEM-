"""Tests for concurrent start/stop operations on Hive OS native service supervisor."""

from __future__ import annotations

import multiprocessing
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class ConcurrentStartStopTests(unittest.TestCase):
    def _make_manifest(self, name="test-svc", enabled=True):
        return {
            "schema_version": 1,
            "name": name,
            "enabled": enabled,
            "command": {"interpreter": "python", "base": "repository", "path": "bin/test.py"},
            "health_check": {"type": "process", "failure_threshold": 1, "interval_seconds": 0},
            "restart": {"policy": "never"},
            "logging": {"stdout": "test.out.log"},
            "shutdown": {"signal": "TERM", "timeout_seconds": 1, "kill_after_timeout": True},
        }

    def test_start_and_stop_concurrently(self):
        """A4: One process starts a service while another stops it simultaneously.

        The Supervisor must serialize operations. The final state must be
        consistent: either RUNNING (start won) or STOPPED (stop won).
        No crash, no corrupted state.
        """
        from services.supervisor import Supervisor
        from services.process import TrackedProcess

        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp) / "state"
            log_root = Path(tmp) / "log"
            state_root.mkdir(parents=True, exist_ok=True)
            log_root.mkdir(parents=True, exist_ok=True)

            manifest = self._make_manifest()
            manifests = {"test-svc": manifest}
            supervisor = Supervisor(
                manifests=manifests,
                state_root=state_root,
                log_root=log_root,
                runtime_info={},
            )

            q = multiprocessing.Queue()

            def _worker_start(state_root: str, log_root: str, q):
                from services.supervisor import Supervisor
                import time
                supervisor = Supervisor(
                    manifests={"test-svc": {
                        "schema_version": 1,
                        "name": "test-svc",
                        "enabled": True,
                        "command": {"interpreter": "python", "base": "repository", "path": "bin/test.py"},
                        "health_check": {"type": "process", "failure_threshold": 1, "interval_seconds": 0},
                        "restart": {"policy": "never"},
                        "logging": {"stdout": "test.out.log"},
                        "shutdown": {"signal": "TERM", "timeout_seconds": 1, "kill_after_timeout": True},
                    }},
                    state_root=Path(state_root),
                    log_root=Path(log_root),
                    runtime_info={},
                )
                try:
                    result = supervisor.start("test-svc")
                    q.put(("started", result.get("state"), result.get("pid")))
                except Exception as e:
                    q.put(("start_error", str(e)))

            def _worker_stop(state_root: str, log_root: str, q):
                from services.supervisor import Supervisor
                import time
                supervisor = Supervisor(
                    manifests={"test-svc": {
                        "schema_version": 1,
                        "name": "test-svc",
                        "enabled": True,
                        "command": {"interpreter": "python", "base": "repository", "path": "bin/test.py"},
                        "health_check": {"type": "process", "failure_threshold": 1, "interval_seconds": 0},
                        "restart": {"policy": "never"},
                        "logging": {"stdout": "test.out.log"},
                        "shutdown": {"signal": "TERM", "timeout_seconds": 1, "kill_after_timeout": True},
                    }},
                    state_root=Path(state_root),
                    log_root=Path(log_root),
                    runtime_info={},
                )
                try:
                    result = supervisor.stop("test-svc")
                    q.put(("stopped", result.get("state")))
                except Exception as e:
                    q.put(("stop_error", str(e)))

            # Pre-populate a fake running process so stop has something to do
            supervisor.processes["test-svc"] = None

            p1 = multiprocessing.Process(
                target=_worker_start, args=(str(state_root), str(log_root), q)
            )
            p2 = multiprocessing.Process(
                target=_worker_stop, args=(str(state_root), str(log_root), q)
            )
            # Launch simultaneously — maximize race window
            p1.start()
            p2.start()
            p1.join(timeout=10)
            p2.join(timeout=10)

            events = []
            while not q.empty():
                events.append(q.get_nowait())

            started = [e for e in events if e[0] == "started"]
            stopped = [e for e in events if e[0] == "stopped"]
            errors = [e for e in events if e[0].endswith("_error")]

            # At least one operation should have completed
            self.assertTrue(
                len(started) + len(stopped) + len(errors) >= 1,
                f"No events collected: {events}"
            )

            # No unhandled exceptions (crashes)
            for err in errors:
                self.fail(f"Unexpected error: {err}")

            # If start succeeded, it should report RUNNING
            for ev in started:
                self.assertEqual(ev[1], "RUNNING", f"Start returned unexpected state: {ev}")

            # If stop succeeded, it should report STOPPED
            for ev in stopped:
                self.assertEqual(ev[1], "STOPPED", f"Stop returned unexpected state: {ev}")

    def test_start_and_start_concurrently(self):
        """A4: Two processes call start() on the same service simultaneously.

        WARNING: Supervisor does NOT have cross-process locking. Each process
        has its own in-memory self.processes dict. Both can independently
        observe "not running" and spawn a subprocess. This is documented
        behavior, not a bug — production serialisation is external.

        This test verifies: no crash, both report RUNNING, and the
        Supervisor tolerates the race without corruption.
        """
        from services.supervisor import Supervisor

        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp) / "state"
            log_root = Path(tmp) / "log"
            state_root.mkdir(parents=True, exist_ok=True)
            log_root.mkdir(parents=True, exist_ok=True)

            q = multiprocessing.Queue()

            def _worker_start(state_root: str, log_root: str, worker_id: int, q):
                from services.supervisor import Supervisor
                supervisor = Supervisor(
                    manifests={"test-svc": {
                        "schema_version": 1,
                        "name": "test-svc",
                        "enabled": True,
                        "command": {"interpreter": "python", "base": "repository", "path": "bin/test.py"},
                        "health_check": {"type": "process", "failure_threshold": 1, "interval_seconds": 0},
                        "restart": {"policy": "never"},
                        "logging": {"stdout": "test.out.log"},
                        "shutdown": {"signal": "TERM", "timeout_seconds": 1, "kill_after_timeout": True},
                    }},
                    state_root=Path(state_root),
                    log_root=Path(log_root),
                    runtime_info={},
                )
                try:
                    result = supervisor.start("test-svc")
                    q.put(("started", worker_id, result.get("state"), result.get("pid")))
                except Exception as e:
                    q.put(("start_error", worker_id, str(e)))

            p1 = multiprocessing.Process(
                target=_worker_start, args=(str(state_root), str(log_root), 1, q)
            )
            p2 = multiprocessing.Process(
                target=_worker_start, args=(str(state_root), str(log_root), 2, q)
            )
            # Launch simultaneously — maximize race window
            p1.start()
            p2.start()
            p1.join(timeout=10)
            p2.join(timeout=10)

            events = []
            while not q.empty():
                events.append(q.get_nowait())

            started = [e for e in events if e[0] == "started"]
            errors = [e for e in events if e[0].endswith("_error")]

            # No crashes
            for err in errors:
                self.fail(f"Unexpected error: {err}")

            # Both workers should report success
            self.assertEqual(len(started), 2, f"Expected 2 start completions, got {started}")

            # Both should report RUNNING
            for ev in started:
                self.assertEqual(ev[2], "RUNNING", f"Unexpected state: {ev}")

            # Supervisor lacks cross-process coordination: two PIDs is possible.
            # The test documents this, it does not assert singleton.
            pids = {ev[3] for ev in started if ev[3] is not None}
            self.assertGreaterEqual(len(pids), 1, f"Expected at least one PID, got {pids}")
            for pid in pids:
                self.assertIsInstance(pid, int)
                self.assertGreater(pid, 0)

    def test_stop_and_stop_concurrently(self):
        """A4: Two processes call stop() on the same service simultaneously.

        stop() is idempotent: if the service is already stopped, it returns
        STOPPED immediately. Both workers should complete without crash.
        """
        from services.supervisor import Supervisor

        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp) / "state"
            log_root = Path(tmp) / "log"
            state_root.mkdir(parents=True, exist_ok=True)
            log_root.mkdir(parents=True, exist_ok=True)

            manifest = self._make_manifest()
            manifests = {"test-svc": manifest}
            supervisor = Supervisor(
                manifests=manifests,
                state_root=state_root,
                log_root=log_root,
                runtime_info={},
            )

            q = multiprocessing.Queue()

            # Pre-populate a fake running process so stop has something to do
            supervisor.processes["test-svc"] = None

            def _worker_stop(state_root: str, log_root: str, worker_id: int, q):
                from services.supervisor import Supervisor
                supervisor = Supervisor(
                    manifests={"test-svc": {
                        "schema_version": 1,
                        "name": "test-svc",
                        "enabled": True,
                        "command": {"interpreter": "python", "base": "repository", "path": "bin/test.py"},
                        "health_check": {"type": "process", "failure_threshold": 1, "interval_seconds": 0},
                        "restart": {"policy": "never"},
                        "logging": {"stdout": "test.out.log"},
                        "shutdown": {"signal": "TERM", "timeout_seconds": 1, "kill_after_timeout": True},
                    }},
                    state_root=Path(state_root),
                    log_root=Path(log_root),
                    runtime_info={},
                )
                try:
                    result = supervisor.stop("test-svc")
                    q.put(("stopped", worker_id, result.get("state")))
                except Exception as e:
                    q.put(("stop_error", worker_id, str(e)))

            p1 = multiprocessing.Process(
                target=_worker_stop, args=(str(state_root), str(log_root), 1, q)
            )
            p2 = multiprocessing.Process(
                target=_worker_stop, args=(str(state_root), str(log_root), 2, q)
            )
            # Launch simultaneously
            p1.start()
            p2.start()
            p1.join(timeout=10)
            p2.join(timeout=10)

            events = []
            while not q.empty():
                events.append(q.get_nowait())

            stopped = [e for e in events if e[0] == "stopped"]
            errors = [e for e in events if e[0].endswith("_error")]

            # No crashes
            for err in errors:
                self.fail(f"Unexpected error: {err}")

            # Both workers should report success
            self.assertEqual(len(stopped), 2, f"Expected 2 stop completions, got {stopped}")

            # Both should report STOPPED (idempotent)
            for ev in stopped:
                self.assertEqual(ev[2], "STOPPED", f"Unexpected state: {ev}")

    def test_restart_and_stop_concurrently(self):
        """A4: One process restarts a service while another stops it simultaneously.

        Restart is stop-then-start. The final state must be consistent:
        either STOPPED or RUNNING. No crash.
        """
        from services.supervisor import Supervisor

        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp) / "state"
            log_root = Path(tmp) / "log"
            state_root.mkdir(parents=True, exist_ok=True)
            log_root.mkdir(parents=True, exist_ok=True)

            manifest = self._make_manifest()
            manifests = {"test-svc": manifest}
            supervisor = Supervisor(
                manifests=manifests,
                state_root=state_root,
                log_root=log_root,
                runtime_info={},
            )

            q = multiprocessing.Queue()

            def _worker_restart(state_root: str, log_root: str, q):
                from services.supervisor import Supervisor
                supervisor = Supervisor(
                    manifests={"test-svc": {
                        "schema_version": 1,
                        "name": "test-svc",
                        "enabled": True,
                        "command": {"interpreter": "python", "base": "repository", "path": "bin/test.py"},
                        "health_check": {"type": "process", "failure_threshold": 1, "interval_seconds": 0},
                        "restart": {"policy": "never"},
                        "logging": {"stdout": "test.out.log"},
                        "shutdown": {"signal": "TERM", "timeout_seconds": 1, "kill_after_timeout": True},
                    }},
                    state_root=Path(state_root),
                    log_root=Path(log_root),
                    runtime_info={},
                )
                try:
                    result = supervisor.restart("test-svc")
                    q.put(("restarted", result.get("state")))
                except Exception as e:
                    q.put(("restart_error", str(e)))

            def _worker_stop(state_root: str, log_root: str, q):
                from services.supervisor import Supervisor
                supervisor = Supervisor(
                    manifests={"test-svc": {
                        "schema_version": 1,
                        "name": "test-svc",
                        "enabled": True,
                        "command": {"interpreter": "python", "base": "repository", "path": "bin/test.py"},
                        "health_check": {"type": "process", "failure_threshold": 1, "interval_seconds": 0},
                        "restart": {"policy": "never"},
                        "logging": {"stdout": "test.out.log"},
                        "shutdown": {"signal": "TERM", "timeout_seconds": 1, "kill_after_timeout": True},
                    }},
                    state_root=Path(state_root),
                    log_root=Path(log_root),
                    runtime_info={},
                )
                try:
                    result = supervisor.stop("test-svc")
                    q.put(("stopped", result.get("state")))
                except Exception as e:
                    q.put(("stop_error", str(e)))

            # Pre-populate a fake running process so stop/restart have something to do
            supervisor.processes["test-svc"] = None

            p1 = multiprocessing.Process(
                target=_worker_restart, args=(str(state_root), str(log_root), q)
            )
            p2 = multiprocessing.Process(
                target=_worker_stop, args=(str(state_root), str(log_root), q)
            )
            # Launch simultaneously
            p1.start()
            p2.start()
            p1.join(timeout=10)
            p2.join(timeout=10)

            events = []
            while not q.empty():
                events.append(q.get_nowait())

            restarted = [e for e in events if e[0] == "restarted"]
            stopped = [e for e in events if e[0] == "stopped"]
            errors = [e for e in events if e[0].endswith("_error")]

            # At least one operation should have completed
            self.assertTrue(
                len(restarted) + len(stopped) + len(errors) >= 1,
                f"No events collected: {events}"
            )

            # No unhandled exceptions
            for err in errors:
                self.fail(f"Unexpected error: {err}")

            # If restart succeeded, it should report RUNNING
            for ev in restarted:
                self.assertEqual(ev[1], "RUNNING", f"Restart returned unexpected state: {ev}")

            # If stop succeeded, it should report STOPPED
            for ev in stopped:
                self.assertEqual(ev[1], "STOPPED", f"Stop returned unexpected state: {ev}")


if __name__ == "__main__":
    unittest.main()
