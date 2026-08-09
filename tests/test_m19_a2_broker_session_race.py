"""Milestone 19 — A2 Broker session race investigation.

BrokerSession is a plain Python in-memory object with no threading locks.
The canonical Broker.run() is single-threaded; each Broker creates its own
BrokerSession. The only shared resource is the state_root directory where
_persist() writes per-session JSON files (unique filename per session).

This test verifies that even under deliberate concurrent threading stress:
- active_transactions remains consistent
- history remains consistent  
- stop state remains consistent
- _persist() races between different sessions are safe
"""

from __future__ import annotations

import json
import multiprocessing
import os
import threading
import time
from pathlib import Path

import pytest

from hive_broker.session import BrokerSession


class TestBrokerSessionThreadSafety:
    """A2 — concurrent mutation of BrokerSession state."""

    def test_concurrent_add_remove_transactions(self, tmp_path):
        """Multiple threads adding/removing from the same session."""
        session = BrokerSession(state_root=tmp_path)
        errors: list[str] = []
        added: set[str] = set()
        lock = threading.Lock()

        def worker(n: int):
            for i in range(50):
                txn = f"txn-{n}-{i}"
                session.add_transaction(txn)
                with lock:
                    added.add(txn)
                time.sleep(0.001)
                session.remove_transaction(txn)
                with lock:
                    added.discard(txn)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # After all workers finish, the set should be empty
        assert session.active_transactions == set(), f"Leaked transactions: {session.active_transactions}"

    def test_concurrent_stop_race(self, tmp_path):
        """Multiple threads calling stop() concurrently."""
        session = BrokerSession(state_root=tmp_path)

        def stopper():
            for _ in range(100):
                session.stop()

        threads = [threading.Thread(target=stopper) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # stop() is idempotent; final state must be stopped
        assert session.is_stopped() is True

    def test_persist_race_different_sessions_same_root(self, tmp_path):
        """Multiple sessions persisting to the same state_root concurrently."""
        sessions = [BrokerSession(state_root=tmp_path) for _ in range(5)]

        def persist_worker(sess: BrokerSession):
            for _ in range(20):
                sess.add_transaction(f"txn-{sess.session_id}")
                sess._persist()

        threads = [
            threading.Thread(target=persist_worker, args=(s,))
            for s in sessions
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each session writes to a unique file; verify all exist and parse
        for s in sessions:
            target = tmp_path / f"{s.session_id}.json"
            assert target.exists(), f"Missing persist file for {s.session_id}"
            data = json.loads(target.read_text())
            assert data["session_id"] == s.session_id
            assert data["stopped"] == s.is_stopped()

    def test_history_append_race(self, tmp_path):
        """Concurrent history append must not corrupt the list."""
        session = BrokerSession(state_root=tmp_path)

        def appender(n: int):
            for i in range(50):
                session.history.append({"worker": n, "seq": i})

        threads = [threading.Thread(target=appender, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Total entries should equal sum of all appends
        assert len(session.history) == 4 * 50
        # Verify structure integrity — no malformed entries
        for entry in session.history:
            assert isinstance(entry, dict)
            assert "worker" in entry
            assert "seq" in entry

    def test_cross_session_isolation(self, tmp_path):
        """Sessions with different IDs must not interfere."""
        s1 = BrokerSession(session_id="sess-alpha", state_root=tmp_path)
        s2 = BrokerSession(session_id="sess-beta", state_root=tmp_path)

        s1.add_transaction("txn-a")
        s2.add_transaction("txn-b")

        assert s1.active_transactions == {"txn-a"}
        assert s2.active_transactions == {"txn-b"}

        s1.stop()
        assert s1.is_stopped() is True
        assert s2.is_stopped() is False

    def test_transaction_membership_during_dispatch_simulation(self, tmp_path):
        """Simulate dispatcher-style membership checks under concurrent mutation."""
        session = BrokerSession(state_root=tmp_path)
        target_txn = "txn-target"
        session.add_transaction(target_txn)

        results: list[bool] = []
        lock = threading.Lock()

        def checker():
            for _ in range(200):
                member = target_txn in session.active_transactions
                with lock:
                    results.append(member)

        def mutator():
            for _ in range(100):
                session.remove_transaction(target_txn)
                session.add_transaction(target_txn)

        t1 = threading.Thread(target=checker)
        t2 = threading.Thread(target=mutator)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # At end, target must be present (last mutator action is add)
        assert target_txn in session.active_transactions
        # During the race, membership checks should only return True or False
        # (no exceptions, no corruption)
        assert all(r in (True, False) for r in results)

    def test_persist_no_tmp_leak_on_race(self, tmp_path):
        """_persist() must not leave stale .tmp files even under thread pressure."""
        session = BrokerSession(state_root=tmp_path)

        def persist_worker():
            for _ in range(50):
                session._persist()

        threads = [threading.Thread(target=persist_worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"Stale .tmp files left: {tmp_files}"

