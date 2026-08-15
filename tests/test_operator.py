"""Tests for operator notes, speak, and shell integration."""

from __future__ import annotations

from pathlib import Path

from hive_operator import clear_notes, disable, enable, notes_info, read_notes, save_notes, speak, status


def test_notes_create_and_read(tmp_path):
    save_notes(tmp_path, "backup vault today\n")
    notes, migrated = read_notes(tmp_path)
    assert notes == "backup vault today\n"
    assert not migrated


def test_notes_legacy_migration(tmp_path, monkeypatch):
    legacy = tmp_path / ".hive_ops.txt"
    legacy.write_text("legacy note", encoding="utf-8")
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    notes, migrated = read_notes(tmp_path / "config")
    assert migrated
    assert notes == "legacy note"


def test_notes_clear(tmp_path):
    save_notes(tmp_path, "hello")
    assert clear_notes(tmp_path)
    assert not (tmp_path / "operator-notes.txt").exists()
    assert not clear_notes(tmp_path)


def test_notes_info(tmp_path):
    save_notes(tmp_path, "info test")
    info = notes_info(tmp_path)
    assert info["exists"]
    assert info["size_bytes"] > 0


def test_speak_deterministic():
    a = speak()
    b = speak()
    assert a == b
    assert "End Transmission" in a


def test_shell_enable_disable(tmp_path):
    rc = tmp_path / ".bashrc"
    result = enable(rc)
    assert result["installed"]
    assert status(rc)["enabled"]
    result2 = enable(rc)
    assert not result2["installed"]
    result3 = disable(rc)
    assert result3["removed"]
    assert not status(rc)["enabled"]
    # Unrelated content preserved.
    text = rc.read_text(encoding="utf-8")
    assert "unrelated" not in text  # we never wrote unrelated; just ensure no crash


def test_shell_preserve_unrelated_content(tmp_path):
    rc = tmp_path / ".bashrc"
    rc.write_text("unrelated line\n", encoding="utf-8")
    enable(rc)
    disable(rc)
    text = rc.read_text(encoding="utf-8")
    assert "unrelated line" in text
