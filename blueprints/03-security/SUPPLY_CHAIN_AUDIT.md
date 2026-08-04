# Supply Chain Audit

## Software sources used by Hive OS

| Source | Purpose | Verification today | Risk |
|--------|---------|----------------------|------|
| GitHub `kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-` | Install/update/repair source code | TLS only | HIGH |
| Termux/F-Droid package repos | System packages (`pkg install`) | TLS + repository trust | MEDIUM |
| PyPI | Python dependencies (`requirements.txt`) | TLS + loose lower-bound pins | HIGH |
| GitHub Actions `actions/checkout@v4`, `actions/setup-python@v5`, `actions/cache@v3`, `actions/upload-artifact@v3` | CI workflow | Trust in upstream tags/SHAs | MEDIUM |

## Dependency pinning

`requirements.txt` uses lower bounds only, e.g.:

```text
requests>=2.31.0
pyyaml>=6.0.1
jsonschema>=4.19.0
...
```

**No upper bounds, no cryptographic hashes, no lock file.** This violates modern supply-chain best practice (Hermes dependency policy requires upper bounds for PyPI packages).

## CI/CD workflow

`.github/workflows/ci.yml`:
- Lints `Hive Ops DevAI` with flake8.
- Runs bandit and safety.
- Builds a tarball excluding `brain-plug/escape_living_ai.txt`.
- Uses `actions/*@v*` tags rather than pinned SHAs.

## Release signing

No evidence of signed releases, release signing keys, or threshold signatures. Tag `v1.0.0` exists but was not verified as signed.

## Update integrity

`update.sh` performs `git pull origin master`. No TUF metadata, no signed snapshots, no anti-rollback protection.

## Required remediation

1. Pin dependencies with `>=floor,<next_major` and generate a `uv.lock`/`poetry.lock` with hashes.
2. Sign release tags and provide reproducible build instructions.
3. Implement TUF-style or signed update metadata.
4. Pin GitHub Actions to commit SHAs.
5. Add SBOM generation for releases.
6. Verify the install script's own integrity with a pinned hash before execution.
