# Plugin Identity Model

Plugin identity is immutable and digest-bound:

- plugin_id
- plugin_version
- manifest_digest
- installation_id
- publisher_id (optional)
- capability_grant_digest
- configuration_digest

Identity propagates into Broker actor, Policy requests, audit, and transaction correlation.
