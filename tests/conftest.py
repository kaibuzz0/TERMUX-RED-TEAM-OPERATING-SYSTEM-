"""Shared pytest compatibility hooks for the Hive test suite."""

from __future__ import annotations

import multiprocessing
import os


# Python 3.14 changed the default POSIX multiprocessing start method away from
# ``fork``. Several real-concurrency tests intentionally define short-lived
# worker functions inside the test body; their purpose is to exercise Hive's
# filesystem locking and crash recovery, not spawn/forkserver pickling rules.
# Preserve the historical POSIX execution model explicitly so those tests keep
# testing the lock semantics consistently across supported Python versions.
if os.name == "posix" and "fork" in multiprocessing.get_all_start_methods():
    multiprocessing.set_start_method("fork", force=True)
