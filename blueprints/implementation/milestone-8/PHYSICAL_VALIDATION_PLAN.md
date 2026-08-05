# Milestone 8 Physical Termux Validation Plan

1. Install the `cryptography` dependency on Termux:
   - `pkg install python rust` (if wheel unavailable)
   - `pip install cryptography==48.0.1` or use prebuilt wheel
2. Benchmark scrypt KDF on the target device with test parameters.
3. Initialize a vault with synthetic password.
4. Unlock, set a synthetic secret, save, lock, and re-unlock.
5. Verify wrong password fails with bounded attempts.
6. Test atomic write interruption (kill process mid-save, verify prior vault intact).
7. Test legacy `.hive_auth/passwd` detection.
8. Verify no shared-storage writes.
9. Verify no shell history leakage (do not type password in command line).
10. Verify no process-list password exposure.

Status: **NOT YET RUN**.
