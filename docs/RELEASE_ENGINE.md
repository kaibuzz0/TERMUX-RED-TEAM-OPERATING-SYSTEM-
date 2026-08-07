# Release Engine

The release engine produces signed, reproducible, offline-installable Hive OS releases.

## Design

- Reuses Milestone 10 signing/trust/manifest/bundle primitives.
- Adds deterministic release versioning, channels, registry, dependency planning, and SBOM.
- Release signing uses Ed25519 offline keys.
- No network required for installation from a complete bundle.
