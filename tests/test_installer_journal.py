"""Tests for installer/journal.py."""

import json
import os
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sequence_numbers_ordered(self):
        from installer.journal import InstallJournal
        j = InstallJournal(self.tmp, "txn-1")
        j.start()
        j.append("op1", "copy", {}, result="completed")
        j.append("op2", "mkdir", {}, result="completed")
        j.close("completed")
        records = j.read()
        self.assertEqual([r["sequence"] for r in records], [1, 2, 3, 4])

    def test_valid_structured_records(self):
        from installer.journal import InstallJournal
        j = InstallJournal(self.tmp, "txn-2")
        j.start()
        records = j.read()
        self.assertTrue(all("timestamp" in r for r in records))
        self.assertTrue(all("transaction_id" in r for r in records))

    def test_rollback_operation_recorded(self):
        from installer.journal import InstallJournal
        j = InstallJournal(self.tmp, "txn-3")
        j.append("op1", "copy", {}, result="completed", rollback_op={"id": "undo-op1", "type": "remove"})
        rec = j.read()[0]
        self.assertEqual(rec["rollback_operation"]["id"], "undo-op1")

    def test_secret_redaction(self):
        from installer.journal import InstallJournal
        j = InstallJournal(self.tmp, "txn-4")
        j.append("op1", "copy", {"password": "secret123", "token": "abc"}, result="completed")
        rec = j.read()[0]
        self.assertEqual(rec["details"]["password"], "[REDACTED]")
        self.assertEqual(rec["details"]["token"], "[REDACTED]")

    def test_incomplete_journal_detectable(self):
        from installer.journal import InstallJournal
        j = InstallJournal(self.tmp, "txn-5")
        j.start()
        j.append("op1", "copy", {}, result="completed")
        self.assertFalse(j.is_complete())

    def test_corrupt_journal_rejected(self):
        from installer.journal import InstallJournal, JournalError
        journal_file = self.tmp / "txn-6.jsonl"
        journal_file.write_text("{not json\n", encoding="utf-8")
        j = InstallJournal(self.tmp, "txn-6")
        with self.assertRaises(JournalError):
            j.read()


if __name__ == "__main__":
    unittest.main()
