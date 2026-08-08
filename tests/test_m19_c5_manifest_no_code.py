"""C5-MANIFEST: Untrusted manifest cannot specify module/function/code execution.

The task manifest schema (`hive_broker/schema.py`) has a strict, bounded field set.
It contains no fields for module names, function references, code strings, or any
form of dynamic execution. Unknown top-level fields are rejected at validation time.

This test verifies the structural impossibility of code-injection through manifests.
"""

from __future__ import annotations

import pytest

from hive_broker.schema import validate_manifest, ManifestError


class TestManifestNoCodeExecutionSurface:
    """Manifest schema rejects any attempt to specify code/module/function."""

    def _make_base(self):
        return {
            "schema_version": 1,
            "task_id": "test-task",
            "requestor": "test",
            "intent": "broker-capabilities",
            "required_capabilities": ["broker.capabilities"],
            "allowed_actions": ["broker.capabilities"],
            "target_services": [],
            "target_paths": [],
            "read_only": True,
            "timeout_seconds": 10,
            "audit_level": "normal",
        }

    # ------------------------------------------------------------------
    # Unknown field rejection
    # ------------------------------------------------------------------

    def test_rejects_module_field(self):
        """Manifest with 'module' field rejected as unknown."""
        raw = self._make_base()
        raw["module"] = "os.system"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_function_field(self):
        """Manifest with 'function' field rejected as unknown."""
        raw = self._make_base()
        raw["function"] = "eval"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_code_field(self):
        """Manifest with 'code' field rejected as unknown."""
        raw = self._make_base()
        raw["code"] = "__import__('os').system('id')"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_script_field(self):
        """Manifest with 'script' field rejected as unknown."""
        raw = self._make_base()
        raw["script"] = "import subprocess; subprocess.run('id')"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_payload_field(self):
        """Manifest with 'payload' field rejected as unknown."""
        raw = self._make_base()
        raw["payload"] = {"cmd": "id"}
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_call_field(self):
        """Manifest with 'call' field rejected as unknown."""
        raw = self._make_base()
        raw["call"] = "exec"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_class_field(self):
        """Manifest with 'class' field rejected as unknown."""
        raw = self._make_base()
        raw["class"] = "subprocess.Popen"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_method_field(self):
        """Manifest with 'method' field rejected as unknown."""
        raw = self._make_base()
        raw["method"] = "run"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_import_field(self):
        """Manifest with 'import' field rejected as unknown."""
        raw = self._make_base()
        raw["import"] = "subprocess"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_eval_field(self):
        """Manifest with 'eval' field rejected as unknown."""
        raw = self._make_base()
        raw["eval"] = "1 + 1"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_exec_field(self):
        """Manifest with 'exec' field rejected as unknown."""
        raw = self._make_base()
        raw["exec"] = "print('pwned')"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    def test_rejects_command_field(self):
        """Manifest with 'command' field rejected as unknown."""
        raw = self._make_base()
        raw["command"] = "rm -rf /"
        with pytest.raises(ManifestError) as exc:
            validate_manifest(raw)
        assert "Unknown manifest fields" in str(exc.value)

    # ------------------------------------------------------------------
    # Allowed fields are bounded
    # ------------------------------------------------------------------

    def test_allowed_fields_list_is_complete(self):
        """validate_manifest only accepts 12 known top-level fields."""
        raw = self._make_base()
        # Adding any one unknown field causes rejection
        for bad_field in (
            "module", "function", "code", "script", "payload", "call",
            "class", "method", "import", "eval", "exec", "command",
            "args", "kwargs", "constructor", "new", "init", "load",
            "source", "bytecode", "ast", "compile", "run", "spawn",
            "shell", "pipe", "fork", "thread", "threading", "asyncio",
            "coroutine", "callback", "hook", "plugin", "extension",
            "dylib", "so", "dll", "lib", "path", "file", "url", "uri",
            "http", "https", "ftp", "socket", "network", "tcp", "udp",
            "ipc", "message", "queue", "channel", "stream", "pipe",
        ):
            test = dict(raw)
            test[bad_field] = "test"
            with pytest.raises(ManifestError) as exc:
                validate_manifest(test)
            assert "Unknown manifest fields" in str(exc.value)

    # ------------------------------------------------------------------
    # No code-execution fields exist in returned manifest
    # ------------------------------------------------------------------

    def test_valid_manifest_has_no_code_fields(self):
        """A validated manifest contains only structural metadata — no code."""
        raw = self._make_base()
        manifest = validate_manifest(raw)
        assert "module" not in manifest
        assert "function" not in manifest
        assert "code" not in manifest
        assert "script" not in manifest
        assert "payload" not in manifest
        assert "call" not in manifest
        assert "eval" not in manifest
        assert "exec" not in manifest

    # ------------------------------------------------------------------
    # allowed_actions are string identifiers, not code references
    # ------------------------------------------------------------------

    def test_allowed_actions_are_string_identifiers(self):
        """allowed_actions is a list of capability strings, not code paths."""
        raw = self._make_base()
        raw["allowed_actions"] = ["broker.capabilities", "service.status"]
        manifest = validate_manifest(raw)
        for action in manifest["allowed_actions"]:
            assert isinstance(action, str)
            assert "." in action  # dotted capability name
            assert "(" not in action  # no function call syntax
            assert " " not in action  # no expression syntax
