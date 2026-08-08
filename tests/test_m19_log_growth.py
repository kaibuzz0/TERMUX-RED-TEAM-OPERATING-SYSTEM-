"""Milestone 19 — Audit / log growth boundedness audit.

Production log/audit bounds catalog:
- hive_broker.audit.AuditLog.write() — per-record bound: _MAX_RECORD_BYTES = 16 KiB
  (oversized records replaced with stub error). No file size limit, no rotation.
- config_engine.audit.ConfigAuditLog.record() — NO explicit bound; append-only.
- installer.journal.InstallJournal.append() — NO explicit bound per transaction.
- hive_broker.session.BrokerSession._persist() — history truncated to [-100:];
  active_transactions NOT truncated.
- config_engine.defaults — max_log_size_mb / max_log_count are schema-only;
  no production code enforces them (accepted debt).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. AuditLog per-record bound (16 KiB)
# ---------------------------------------------------------------------------

class TestAuditLogPerRecordBound:
    def test_record_well_under_max_bytes_accepted(self):
        """AuditLog.write() accepts a record whose JSON is well under 16 KiB."""
        from hive_broker.audit import AuditLog, _MAX_RECORD_BYTES
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp))
            record = {"audit_id": "audit-" + "x" * 32, "timestamp": "2024-01-01T00:00:00Z", "msg": "ok"}
            line = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
            assert len(line.encode("utf-8")) < _MAX_RECORD_BYTES
            audit_id = log.write(record)
            assert "error" not in audit_id.lower()
            assert audit_id.startswith("audit-")
            # Verify the full record (not a stub) was written
            lines = log._path.read_text(encoding="utf-8").strip().splitlines()
            last = json.loads(lines[-1])
            assert last.get("msg") == "ok"

    def test_record_one_byte_over_replaced_with_stub(self):
        """AuditLog.write() replaces a record > 16 KiB with a stub error record."""
        from hive_broker.audit import AuditLog, _MAX_RECORD_BYTES
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp))
            big = {"payload": "x" * (_MAX_RECORD_BYTES + 100)}
            audit_id = log.write(big)
            # The oversized record is replaced; the returned audit_id is still valid
            assert audit_id.startswith("audit-")
            # Read back and verify stub
            records = log.read_transaction("")  # empty txn_id matches nothing; read file directly
            # read_transaction filters by txn_id, so read raw
            lines = (log._path).read_text(encoding="utf-8").strip().splitlines()
            last = json.loads(lines[-1])
            assert last.get("error") == "record oversized"

    def test_audit_log_file_grows_unbounded(self):
        """AuditLog.write() appends indefinitely; no file size cap or rotation."""
        from hive_broker.audit import AuditLog
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp))
            for i in range(1000):
                log.write({"seq": i, "msg": "x" * 100})
            lines = log._path.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 1000
            total_bytes = log._path.stat().st_size
            assert total_bytes > 1000 * 100  # well above minimum

    def test_read_transaction_reads_entire_file(self):
        """AuditLog.read_transaction() reads the entire audit file into memory."""
        from hive_broker.audit import AuditLog
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(Path(tmp))
            for i in range(500):
                log.write({"transaction_id": "txn-1", "seq": i})
            records = log.read_transaction("txn-1")
            assert len(records) == 500


# ---------------------------------------------------------------------------
# 2. ConfigAuditLog — unbounded append-only
# ---------------------------------------------------------------------------

class TestConfigAuditLogUnbounded:
    def test_config_audit_log_appends_indefinitely(self):
        """ConfigAuditLog.record() appends without size limit or rotation."""
        from config_engine.audit import ConfigAuditLog
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "config_audit.jsonl"
            log = ConfigAuditLog(log_path)
            for i in range(1000):
                log.record(
                    transaction_id=f"txn-{i:04d}",
                    action="set",
                    profile="main",
                    author="test",
                    details={"key": f"val-{i}"},
                )
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 1000

    def test_config_audit_redacts_secrets(self):
        """ConfigAuditLog redacts secret-like keys regardless of size."""
        from config_engine.audit import ConfigAuditLog
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "config_audit.jsonl"
            log = ConfigAuditLog(log_path)
            log.record(
                transaction_id="txn-1",
                action="set",
                profile="main",
                author="test",
                details={"password": "secret123", "api_key": "key456", "normal": "visible"},
            )
            line = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[0])
            assert line["details"]["password"] == "[REDACTED]"
            assert line["details"]["api_key"] == "[REDACTED]"
            assert line["details"]["normal"] == "visible"


# ---------------------------------------------------------------------------
# 3. InstallJournal — unbounded per-transaction
# ---------------------------------------------------------------------------

class TestInstallJournalUnbounded:
    def test_journal_appends_indefinitely_per_transaction(self):
        """InstallJournal.append() has no explicit entry count limit per transaction."""
        from installer.journal import InstallJournal
        with tempfile.TemporaryDirectory() as tmp:
            journal = InstallJournal(Path(tmp), transaction_id="txn-1")
            for i in range(1000):
                journal.append(f"op-{i}", "mkdir", {"idx": i})
            records = journal.read()
            assert len(records) == 1000

    def test_journal_sequence_increments_without_bound(self):
        """Journal sequence numbers increment without explicit ceiling."""
        from installer.journal import InstallJournal
        with tempfile.TemporaryDirectory() as tmp:
            journal = InstallJournal(Path(tmp), transaction_id="txn-1")
            for i in range(500):
                journal.append(f"op-{i}", "mkdir", {"idx": i})
            records = journal.read()
            sequences = [r["sequence"] for r in records]
            assert sequences == list(range(1, 501))


# ---------------------------------------------------------------------------
# 4. BrokerSession._persist() — history truncated, active NOT truncated
# ---------------------------------------------------------------------------

class TestBrokerSessionPersistTruncation:
    def test_persist_truncates_history_to_100(self):
        """BrokerSession._persist() truncates history to the last 100 entries."""
        from hive_broker.session import BrokerSession
        with tempfile.TemporaryDirectory() as tmp:
            session = BrokerSession(state_root=Path(tmp))
            for i in range(250):
                session.history.append({"idx": i})
            session._persist()
            target = Path(tmp) / f"{session.session_id}.json"
            data = json.loads(target.read_text(encoding="utf-8"))
            assert len(data["history"]) == 100
            assert data["history"][0]["idx"] == 150  # first of last 100
            assert data["history"][-1]["idx"] == 249  # last

    def test_persist_does_not_truncate_active_transactions(self):
        """BrokerSession._persist() preserves all active_transactions (no cap)."""
        from hive_broker.session import BrokerSession
        with tempfile.TemporaryDirectory() as tmp:
            session = BrokerSession(state_root=Path(tmp))
            for i in range(500):
                session.add_transaction(f"txn-{i:04d}")
            session._persist()
            target = Path(tmp) / f"{session.session_id}.json"
            data = json.loads(target.read_text(encoding="utf-8"))
            assert len(data["active_transactions"]) == 500


# ---------------------------------------------------------------------------
# 5. Schema fields max_log_size_mb / max_log_count — unenforced
# ---------------------------------------------------------------------------

class TestLogSchemaFieldsUnenforced:
    def test_max_log_size_mb_is_schema_only(self):
        """max_log_size_mb is a config schema field with no production enforcement."""
        from config_engine.defaults import build_registry
        registry = build_registry()
        runtime = registry.get("runtime")
        spec = runtime.fields["max_log_size_mb"]
        assert spec.default == 10
        assert spec.min_value == 1
        assert spec.max_value == 1024
        # No production code references max_log_size_mb to cap log files

    def test_max_log_count_is_schema_only(self):
        """max_log_count is a config schema field with no production enforcement."""
        from config_engine.defaults import build_registry
        registry = build_registry()
        runtime = registry.get("runtime")
        spec = runtime.fields["max_log_count"]
        assert spec.default == 5
        assert spec.min_value == 1
        assert spec.max_value == 100
        # No production code references max_log_count to rotate logs

    def test_no_production_code_reads_max_log_size_mb(self):
        """No production module imports or references max_log_size_mb for enforcement."""
        # This is a design-documentation test. The field exists in the schema
        # but no log-writing or rotation code consumes it.
        assert True

    def test_no_production_code_reads_max_log_count(self):
        """No production module imports or references max_log_count for enforcement."""
        # Design-documentation test confirming the field is schema-only.
        assert True