# Reusable Repository Toolsets

Repo-engineering utilities imported from trusted sibling repositories. This directory is intentionally under `blueprints/` so it is excluded from Hive runtime/release manifests.

Each toolset is self-contained and must include purpose, usage, maturity, provenance, and machine-readable metadata.

Imported toolsets:

- `repo-factory/` — AI-friendly repository bootstrap and diagnostic CI templates, sourced from `kaibuzz0/cipher-solving-suite`.
- `github-repo-ops/` — bounded repository snapshot/onboarding utilities, sourced from `kaibuzz0/Git-hub-command-site`.

These are developer/repository tools, not Hive runtime components. Do not move them into the signed runtime without a separate release-scope review.
