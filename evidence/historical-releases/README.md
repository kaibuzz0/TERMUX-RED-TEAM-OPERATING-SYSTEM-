# Historical release artifacts

This directory contains previously shipped release artifacts kept for
reference, audit continuity, and historical verification only. They are
**not** used by current bootstrap, update, or release verification code.

## Canonical trust anchor

The single authoritative production trust-store file is:

    updates/trust_store/hive-release.pem

All verification code loads that path via `updates.trust.TRUST_STORE_PATH`.

## Historical copies

- `1.0.0/hive-release.pem` — byte-identical copy of the `releases/1.0.0/hive-release.pem`
  duplicate that was removed to consolidate trust anchors.
- `1.0.0/hive-os-1.0.0-release.*` — the original 1.0.0 signed release bundle and manifest.
