# ADR-0007: Dependency Authority

## Status

Proposed.

## Context

The repository currently has only a loose `requirements.txt`. A single source of truth is needed for reproducible, verifiable builds on ARM64 Termux.

## Decision

**Authoritative source:** `pyproject.toml` with a generated `requirements-lock.txt` containing pinned versions and hashes.

Rationale:
- `pyproject.toml` is the modern Python packaging standard.
- Generates `requirements-lock.txt` for environments without `uv`.
- Does not require `uv` on the target device.
- Supports offline installation from lock file.
- Hashes provide supply-chain verification.
- Resolver availability: `pip` can install from lock file; `uv` can generate it on dev host.

**Compatibility exports:**
- `requirements.txt` becomes a generated file with a header: `# Generated from pyproject.toml via scripts/generate-requirements-lock.py`.
- `requirements-lock.txt` is the authoritative lock.

## Consequences

- Developers update `pyproject.toml`, then regenerate lock.
- Termux install can use `pip install -r requirements-lock.txt`.
- No runtime dependency on `uv` on Android.

## Rejected alternatives

- `uv.lock` as primary — rejected because `uv` Termux support is unverified.
- `requirements.txt` as primary — rejected because it lacks hashes and upper bounds.
