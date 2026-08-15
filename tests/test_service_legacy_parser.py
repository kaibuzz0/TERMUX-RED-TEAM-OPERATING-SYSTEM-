"""Tests for safe legacy .svc parser."""

from __future__ import annotations

from services.legacy import build_migration_plan, parse_svc_file


def _write_svc(path, content):
    path.write_text(content, encoding="utf-8")


def test_safe_legacy_fields_parsed(tmp_path):
    svc = tmp_path / "test.svc"
    _write_svc(svc, "START=\"python -m http.server 11434\"\nPROBE=\"curl -s http://127.0.0.1:11434\"\nREQUIRES_NET=1\nUSE_PROXY_ENV=0\nWANT_TORSOCKS=0\nLOG=\"mini-ai.log\"\n")
    parsed = parse_svc_file(svc)
    assert parsed["assignments"]["START"] == "python -m http.server 11434"
    assert parsed["assignments"]["REQUIRES_NET"] == "1"


def test_command_substitution_rejected(tmp_path):
    svc = tmp_path / "bad.svc"
    _write_svc(svc, 'START="python $(which server).py"')
    parsed = build_migration_plan(svc)
    assert parsed["classification"] == "UNSUPPORTED_SHELL"


def test_pipeline_rejected(tmp_path):
    svc = tmp_path / "bad.svc"
    _write_svc(svc, 'START="python server.py | logger"')
    parsed = build_migration_plan(svc)
    assert parsed["classification"] == "UNSUPPORTED_SHELL"


def test_broad_kill_rejected(tmp_path):
    svc = tmp_path / "bad.svc"
    _write_svc(svc, 'START="python server.py"\nPROBE="pkill server"')
    parsed = build_migration_plan(svc)
    assert parsed["classification"] == "DANGEROUS"
