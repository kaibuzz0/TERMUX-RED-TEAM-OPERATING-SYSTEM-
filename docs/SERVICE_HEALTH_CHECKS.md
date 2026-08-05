# Service Health Checks

Supported types:

- `process`: verify tracked process identity.
- `command`: run explicit argument array with timeout.
- `tcp-local`: connect to a loopback address and port.
- `file`: verify file existence and optional freshness.
- `none`: explicit no-op.

Remote network health checks are not implemented in Milestone 11.
