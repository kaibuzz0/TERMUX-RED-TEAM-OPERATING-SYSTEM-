# Plugin Dependencies

Dependency resolution is deterministic planning only.

Supported checks:

- plugin existence
- version range
- Hive version compatibility
- SDK version compatibility
- missing capability
- cycles

Resolution does not execute pip/pkg/apt/curl/wget or arbitrary scripts.
