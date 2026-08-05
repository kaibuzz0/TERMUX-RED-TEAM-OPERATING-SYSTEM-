"""Tests for Hive OS native service supervisor."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class ManifestSchemaTests(unittest.TestCase):
    def test_valid_manifest(self):
        from services.schema import validate_manifest
        m = {
            "schema_version": 1,
            "name": "test-svc",
            "command": {"interpreter": "python", "base": "repository", "path": "bin/test.py", "args": ["arg1"]},
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
            "logging": {"stdout": "test.out.log"},
        }
        self.assertEqual(validate_manifest(m)["name"], "test-svc")

    def test_unknown_schema(self):
        from services.schema import validate_manifest, ServiceConfigError
        with self.assertRaises(ServiceConfigError):
            validate_manifest({"schema_version": 99})

    def test_invalid_service_name(self):
        from services.schema import validate_manifest, ServiceConfigError
        with self.assertRaises(ServiceConfigError):
            validate_manifest({"schema_version": 1, "name": "bad name", "command": {"interpreter": "python"}})

    def test_unknown_interpreter(self):
        from services.schema import validate_manifest, ServiceConfigError
        with self.assertRaises(ServiceConfigError):
            validate_manifest({"schema_version": 1, "name": "x", "command": {"interpreter": "perl"}})

    def test_unknown_path_base(self):
        from services.schema import validate_manifest, ServiceConfigError
        with self.assertRaises(ServiceConfigError):
            validate_manifest({"schema_version": 1, "name": "x", "command": {"interpreter": "python", "base": "external"}})

    def test_traversal_in_command_args(self):
        from services.schema import validate_manifest, ServiceConfigError
        with self.assertRaises(ServiceConfigError):
            validate_manifest({"schema_version": 1, "name": "x", "command": {"interpreter": "python", "args": ["../etc"]}})

    def test_unknown_restart_policy(self):
        from services.schema import validate_manifest, ServiceConfigError
        with self.assertRaises(ServiceConfigError):
            validate_manifest({"schema_version": 1, "name": "x", "command": {"interpreter": "python"}, "restart": {"policy": "explode"}})

    def test_unknown_health_type(self):
        from services.schema import validate_manifest, ServiceConfigError
        with self.assertRaises(ServiceConfigError):
            validate_manifest({"schema_version": 1, "name": "x", "command": {"interpreter": "python"}, "health_check": {"type": "http"}})


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.state = self.tmp / "state"
        self.state.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, d, name, manifest):
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(json.dumps(manifest), encoding="utf-8")

    def test_loads_manifests_deterministically(self):
        from services.registry import ServiceRegistry
        reg = ServiceRegistry(self.repo, self.state)
        svc_dir = self.repo / "services.d"
        self._write(svc_dir, "b.json", {"schema_version": 1, "name": "b", "command": {"interpreter": "python"}})
        self._write(svc_dir, "a.json", {"schema_version": 1, "name": "a", "command": {"interpreter": "python"}})
        reg.load([svc_dir])
        self.assertEqual(reg.list(), ["a", "b"])

    def test_duplicate_name_rejected(self):
        from services.registry import ServiceRegistry
        from services.errors import ServiceConfigError
        reg = ServiceRegistry(self.repo, self.state)
        svc_dir1 = self.repo / "svc1"
        svc_dir2 = self.repo / "svc2"
        self._write(svc_dir1, "x.json", {"schema_version": 1, "name": "x", "command": {"interpreter": "python"}})
        self._write(svc_dir2, "x.json", {"schema_version": 1, "name": "x", "command": {"interpreter": "python"}})
        with self.assertRaises(ServiceConfigError):
            reg.load([svc_dir1, svc_dir2])

    def test_user_override_precedence(self):
        from services.registry import ServiceRegistry
        reg = ServiceRegistry(self.repo, self.state)
        repo_dir = self.repo / "repo.d"
        user_dir = self.repo / "user.d"
        self._write(repo_dir, "x.json", {"schema_version": 1, "name": "x", "command": {"interpreter": "python"}})
        self._write(user_dir, "x.json", {"schema_version": 1, "name": "x", "command": {"interpreter": "python"}})
        reg.load([repo_dir], [user_dir])
        self.assertEqual(reg.native["x"]["command"]["interpreter"], "python")

    def test_user_override_broadening_rejected(self):
        from services.registry import ServiceRegistry
        reg = ServiceRegistry(self.repo, self.state)
        repo_dir = self.repo / "repo.d"
        user_dir = self.repo / "user.d"
        self._write(repo_dir, "x.json", {"schema_version": 1, "name": "x", "command": {"interpreter": "python"}})
        self._write(user_dir, "x.json", {"schema_version": 1, "name": "x", "command": {"interpreter": "bash"}})
        reg.load([repo_dir], [user_dir])
        self.assertIn("x", [n for n, _ in reg.unsupported])


class DependencyGraphTests(unittest.TestCase):
    def test_simple_ordering(self):
        from services.graph import DependencyGraph
        g = DependencyGraph({
            "a": {"dependencies": []},
            "b": {"dependencies": ["a"]},
        })
        self.assertEqual(g.order(), ["a", "b"])

    def test_missing_dependency(self):
        from services.graph import DependencyGraph, ServiceDependencyError
        g = DependencyGraph({"a": {"dependencies": ["missing"]}})
        with self.assertRaises(ServiceDependencyError):
            g.order()

    def test_cycle_detection(self):
        from services.graph import DependencyGraph, ServiceDependencyError
        g = DependencyGraph({"a": {"dependencies": ["b"]}, "b": {"dependencies": ["a"]}})
        with self.assertRaises(ServiceDependencyError):
            g.order()

    def test_reverse_shutdown_order(self):
        from services.graph import DependencyGraph
        g = DependencyGraph({"a": {"dependencies": []}, "b": {"dependencies": ["a"]}})
        self.assertEqual(g.shutdown_order(["a", "b"]), ["b", "a"])


class ProcessIdentityTests(unittest.TestCase):
    def test_stale_pid(self):
        from services.process import TrackedProcess
        # Use a very high PID unlikely to exist.
        manifest = {"name": "x"}
        tp = TrackedProcess(manifest, ["sleep", "10"], "sid")
        self.assertFalse(tp.validate_identity(99999999))

    def test_command_digest_matches(self):
        from services.process import _command_digest
        d1 = _command_digest(["python", "-c", "pass"])
        d2 = _command_digest(["python", "-c", "pass"])
        self.assertEqual(d1, d2)


class RestartPolicyTests(unittest.TestCase):
    def test_never_policy(self):
        from services.restart import RestartPolicy
        p = RestartPolicy({"restart": {"policy": "never"}})
        restart, delay = p.should_restart("x", 1, False)
        self.assertFalse(restart)

    def test_on_failure_restarts(self):
        from services.restart import RestartPolicy
        p = RestartPolicy({"restart": {"policy": "on-failure", "max_attempts": 3}})
        restart, delay = p.should_restart("x", 1, False)
        self.assertTrue(restart)

    def test_crash_loop_after_max(self):
        from services.restart import RestartPolicy
        from services.errors import ServiceRuntimeError
        p = RestartPolicy({"restart": {"policy": "always", "max_attempts": 2}})
        p.should_restart("x", 1, False)
        p.should_restart("x", 1, False)
        with self.assertRaises(ServiceRuntimeError):
            p.should_restart("x", 1, False)


class HealthCheckTests(unittest.TestCase):
    def test_tcp_local_loopback_ok(self):
        from services.health import HealthCheck
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        _, port = s.getsockname()
        s.listen(1)
        try:
            hc = HealthCheck({"health_check": {"type": "tcp-local", "host": "127.0.0.1", "port": port}})
            self.assertTrue(hc.check(None, Path("/tmp"))["healthy"])
        finally:
            s.close()

    def test_tcp_local_remote_rejected(self):
        from services.health import HealthCheck
        hc = HealthCheck({"health_check": {"type": "tcp-local", "host": "8.8.8.8", "port": 53}})
        result = hc.check(None, Path("/tmp"))
        self.assertFalse(result["healthy"])
        self.assertIn("Non-loopback", result["error"])


class SupervisorLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / "state"
        self.logs = self.tmp / "logs"
        self.state.mkdir()
        self.logs.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fixture_manifest(self, enabled=False):
        return {
            "schema_version": 1,
            "name": "sleeper",
            "enabled": enabled,
            "command": {"interpreter": "python", "base": "repository", "path": "tests/fixtures/services/sleeper.py", "args": ["30"]},
            "working_directory": {"base": "temp-root", "path": "."},
            "environment": {"allow": [], "set": {}},
            "dependencies": [],
            "health_check": {"type": "process"},
            "restart": {"policy": "never"},
            "shutdown": {"signal": "TERM", "timeout_seconds": 2, "kill_after_timeout": True},
        }

    def test_disabled_service_rejected(self):
        from services.supervisor import Supervisor
        sup = Supervisor({"sleeper": self._fixture_manifest(enabled=False)}, self.state, self.logs, {})
        from services.errors import ServiceRuntimeError
        with self.assertRaises(ServiceRuntimeError):
            sup.start("sleeper")

    def test_status_non_mutating(self):
        from services.supervisor import Supervisor
        sup = Supervisor({"sleeper": self._fixture_manifest(enabled=False)}, self.state, self.logs, {})
        st = sup.status("sleeper")
        self.assertEqual(st["state"], "STOPPED")


class LegacyAdapterTests(unittest.TestCase):
    def test_no_shell_sourcing(self):
        from services.legacy import parse_svc_file
        tmp = Path(tempfile.mkdtemp())
        svc = tmp / "mini-ai.svc"
        svc.write_text("START='python -m http.server 11434'\nPROBE='nc -z 127.0.0.1 11434'\n", encoding="utf-8")
        try:
            parsed = parse_svc_file(svc)
            self.assertEqual(parsed["assignments"]["START"], "python -m http.server 11434")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_command_substitution_classified_unsupported(self):
        from services.legacy import parse_svc_file
        tmp = Path(tempfile.mkdtemp())
        svc = tmp / "bad.svc"
        svc.write_text("START='python -c \"$(echo foo)\"'\n", encoding="utf-8")
        try:
            parsed = parse_svc_file(svc)
            self.assertEqual(parsed["classification"], "UNSUPPORTED_SHELL")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)



class PathResolutionTests(unittest.TestCase):
    def test_resolve_from_module_file(self):
        from lib.hive_path import resolve_repository_root_from_file
        root = resolve_repository_root_from_file(REPO_ROOT / "services" / "cli.py")
        self.assertEqual(root, REPO_ROOT)

    def test_env_override(self):
        import os
        from lib.hive_path import resolve_repository_root
        old = os.environ.get("HIVE_REPO_ROOT")
        os.environ["HIVE_REPO_ROOT"] = str(REPO_ROOT)
        try:
            root = resolve_repository_root()
            self.assertEqual(root, REPO_ROOT)
        finally:
            if old is None:
                os.environ.pop("HIVE_REPO_ROOT", None)
            else:
                os.environ["HIVE_REPO_ROOT"] = old

    def test_fake_cwd_rejected(self):
        import os
        import tempfile
        from lib.hive_path import resolve_repository_root, PathResolutionError
        tmp = Path(tempfile.mkdtemp())
        (tmp / "hive-canonical.json").write_text("{}", encoding="utf-8")
        old = os.getcwd()
        os.chdir(str(tmp))
        try:
            with self.assertRaises(PathResolutionError):
                resolve_repository_root()
        finally:
            os.chdir(old)
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class ProductionFixtureIsolationTests(unittest.TestCase):
    def test_production_registry_excludes_test_fixtures(self):
        from services.registry import ServiceRegistry
        from lib.hive_path import resolve_state_root
        reg = ServiceRegistry(REPO_ROOT, resolve_state_root())
        reg.load([REPO_ROOT / "Hive Ops Final" / "etc" / "services.d"])
        self.assertNotIn("fixture-http", reg.list())

    def test_test_fixtures_loadable_explicitly(self):
        from services.registry import ServiceRegistry
        from lib.hive_path import resolve_state_root
        reg = ServiceRegistry(REPO_ROOT, resolve_state_root())
        fixture_dir = REPO_ROOT / "tests" / "fixtures" / "services" / "manifests"
        reg.load([fixture_dir])
        self.assertIn("fixture-http", reg.list())



class ProcessIdentityFailClosedTests(unittest.TestCase):
    def test_terminate_unverified_identity_aborts(self):
        from services.process import TrackedProcess
        manifest = {"name": "x"}
        tp = TrackedProcess(manifest, ["sleep", "10"], "sid")
        result = tp.terminate("TERM", 2, True)
        self.assertFalse(result["signaled"])
        self.assertEqual(result["reason"], "no process")

    def test_terminate_rejects_mismatched_start_time(self):
        # Simulate a tracked process with a start time far in the future.
        import subprocess
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        from services.process import TrackedProcess
        manifest = {"name": "x"}
        tp = TrackedProcess(manifest, [sys.executable, "-c", "pass"], "sid")
        tp._proc = proc
        tp.start_time = time.time() + 3600  # impossible future time
        result = tp.terminate("TERM", 2, True)
        self.assertFalse(result["signaled"])
        self.assertEqual(result["reason"], "process identity unverified")
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    unittest.main()
