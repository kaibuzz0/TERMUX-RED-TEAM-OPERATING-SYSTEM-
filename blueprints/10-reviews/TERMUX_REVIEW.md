# Termux Review

## Scope

Review platform profiles, lifecycle, storage, battery/thermal, and device assumptions.

## Findings

### Standard profile
- Status: **PASS**. Accurately lists what standard Termux can and cannot provide.

### Lifecycle
- Status: **PASS**. Acknowledges Android may kill Termux.

### Storage
- Status: **PASS**. Uses app-private storage by default; shared storage opt-in.

### Battery/thermal
- Status: **PASS**. No default wake locks or background polling.

### Concerns
- Need to verify Python 3.11+ availability on older Termux installs.
- Need to test native-extension compilation for `cryptography` on ARM64 Termux.

## Blockers

None for blueprint freeze, but physical validation is required before release.
