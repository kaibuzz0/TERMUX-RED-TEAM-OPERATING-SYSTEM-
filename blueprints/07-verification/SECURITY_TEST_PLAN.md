# Security Test Plan

## Static analysis

- Bandit scan of Python code.
- ShellCheck or similar for shell scripts.
- Regex scan for risky patterns (`curl | bash`, `rm -rf`, `eval`, `0.0.0.0`).
- Dependency audit (pinned hashes, no upper-bound violations).

## Invariant tests

- Verify no base64/plaintext credential storage.
- Verify no unverified remote execution.
- Verify no non-loopback default binding.
- Verify max_delegations=0.
- Verify no Hermes core modification.

## Penetration-style tests

- Attempt to bypass session gate by opening new Termux session.
- Attempt to read vault file without passphrase.
- Attempt to escalate agent task outside allowed paths.
- Attempt to bind a service to `0.0.0.0` without explicit config.
- Attempt to downgrade via update anti-rollback test.

## Physical device tests

- Confirm session gate is bypassable by another Termux session.
- Confirm same-UID process can read unlocked vault memory (if testable safely).
- Confirm network visibility module reports actual listeners.
