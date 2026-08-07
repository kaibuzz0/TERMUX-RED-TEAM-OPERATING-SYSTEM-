# Release Trust

Trust states:

- `UNSIGNED`
- `SIGNED_UNTRUSTED`
- `SIGNED_TRUSTED`
- `INVALID_SIGNATURE`
- `REVOKED`

Unknown, revoked, malformed, or mismatched signatures fail closed.

Trust store is a PEM public-key file with key_id comments.
