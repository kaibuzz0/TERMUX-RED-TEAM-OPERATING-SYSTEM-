# Release Signing

Reuses Milestone 10 Ed25519 signing.

```bash
hive release sign --metadata dist/hive-os-1.0.0-local.metadata.json                   --private-key /secure/release.key                   --key-id release-1                   --output dist/hive-os-1.0.0-local.signed.json
```

Private keys are never committed and never required on the target device.
