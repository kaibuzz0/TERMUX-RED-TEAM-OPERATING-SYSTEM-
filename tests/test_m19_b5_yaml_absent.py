"""B5: Verify unsafe YAML parsing is absent from production paths."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import config_engine.loader as loader_mod


def test_no_unsafe_yaml_load_in_production_source():
    """AST-scan config_engine/loader.py — no yaml.load call may exist."""
    src = Path(inspect.getfile(loader_mod)).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "load"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "yaml"
        ):
            raise AssertionError("Unsafe yaml.load found in production source")
