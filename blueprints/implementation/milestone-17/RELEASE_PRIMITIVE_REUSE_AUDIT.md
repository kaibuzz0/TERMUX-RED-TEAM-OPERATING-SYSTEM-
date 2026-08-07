# Release Primitive Reuse Audit

Existing Milestone 10 release primitives in `updates/`:

| File | Classification | Notes |
|---|---|---|
| `metadata.py` | REUSE_DIRECTLY or EXTEND | """Versioned release metadata format and validation.""" (6151 bytes) |
| `signing.py` | REUSE_DIRECTLY or EXTEND | """Ed25519 signing helpers. (2913 bytes) |
| `trust.py` | REUSE_DIRECTLY or EXTEND | """Trust levels and trust-store helpers.""" (3573 bytes) |
| `manifest.py` | REUSE_DIRECTLY or EXTEND | """Release manifest generation and validation.""" (3415 bytes) |
| `bundle.py` | REUSE_DIRECTLY or EXTEND | """Offline bundle creation, extraction, and safety validation.""" (5109 bytes) |
| `verifier.py` | REUSE_DIRECTLY or EXTEND | """Bundle verification orchestrator.""" (2560 bytes) |
| `updater.py` | REUSE_DIRECTLY or EXTEND | """Update application using the installer activation engine.""" (2806 bytes) |
| `recovery.py` | REUSE_DIRECTLY or EXTEND | """Tiered recovery actions.""" (2284 bytes) |

## Decision

- Reuse existing `updates/signing.py`, `updates/trust.py`, `updates/verifier.py`, `updates/bundle.py` for release signing/trust/verification/archive handling.
- Extend `updates/manifest.py` and `updates/metadata.py` with release-specific fields only if needed.
- Avoid creating a second Ed25519 verifier, trust store, canonical JSON encoder, or safe archive extractor.
- Create `release_engine/` as an adapter/coordination layer above the proven primitives.
