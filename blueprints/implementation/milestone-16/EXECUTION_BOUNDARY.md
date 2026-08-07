# Execution Boundary

Milestone 16 does not load arbitrary third-party Python modules into the core Hive process.

## Preferred Model

- SDK and manifest architecture
- Trusted built-in example plugins
- Read-only execution
- Subprocess isolation where practical

## Subprocess Constraints

If subprocess execution is used:

- explicit Python interpreter
- fixed entrypoint
- minimal environment
- restricted working directory
- no shell
- timeout
- bounded stdout/stderr
- transaction ID
- plugin identity
- broker-only access
- no inherited secrets
- no auto-restart
- no public listener


## Limitation

Third-party plugin subprocess execution is **designed but not yet enabled** in Milestone 16.
Same-process untrusted plugin loading is **not supported**.
