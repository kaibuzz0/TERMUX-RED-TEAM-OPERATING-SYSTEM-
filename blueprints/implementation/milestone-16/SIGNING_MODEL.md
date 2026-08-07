# Signing Model

Trust states are metadata-only in Milestone 16.

- UNSIGNED plugins may be denied in production.
- SIGNED_UNTRUSTED is not silently treated as trusted.
- SIGNED_TRUSTED requires trust store integration (deferred).
- INVALID_SIGNATURE and REVOKED are denied.


## Limitation

Real production Ed25519 plugin signature verification is **DEFERRED** to Milestone 17.
Trust-state metadata exists and policy may deny unsigned plugins, but cryptographic verification is not yet wired.
