# Version Compatibility

Capability negotiation is the primary compatibility contract.

`allowed_since_commit` is an optional development check.

The broker supports:
- semantic version
- capability set
- manifest schema version
- optional build ID
- optional source commit

Rules:
- Packaged runtime without `.git` must still work.
- Unknown manifest schema fails.
- Missing required capability fails.
- Unsupported broker major version fails.
- Optional commit check runs only when repository metadata is available.
- Commit comparison must use actual ancestry checks when Git is available, not lexical hash comparison.
