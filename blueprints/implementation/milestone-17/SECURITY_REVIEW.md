# Security Review

Production release_engine code scanned for:

- shell=True, os.system, eval, exec of untrusted input
- curl, wget, git pull/clone in production installer
- pip/pkg/apt install
- extractall, unsafe archive extraction
- trust-all, skip-verification
- embedded private keys
- hardcoded secrets
- network dependency
- public listener
- unbounded extraction
- in-place active runtime overwrite

Result: clean.
