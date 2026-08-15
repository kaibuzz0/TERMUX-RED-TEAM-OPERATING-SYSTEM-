# Hive OS 1.1 Original Runtime Parity — Update Test

**Version:** 1.1.0-rc.1  
**Channel:** parity-test  
**Source commit:** `e9d342bf83629d1a964ccb81c5851dc5a9b9f39e`  
**Status:** candidate ready for physical Termux self-upgrade

---

## Goal

Update the existing Termux Hive installation **through Hive's own signed
update engine**, not via `git pull` or manual copy, to the OG+modern parity
candidate. Then roll back and re-apply.

---

## What is in the candidate

Recovered and rebuilt:

- Network profiles (`DIRECT`, `ORBOT`, `TOR`, `HOLD`) and health model
- Fail-closed supervised services with exact process ownership
- Crash-loop protection and dependency graph
- `hive health`, `hive doctor`, `hive audit`, `hive selftest`
- Unified runtime logging with rotation
- Hive Operator Home with real telemetry
- Operator notes and `hive speak`
- Optional shell integration for bash/zsh
- Broker/policy read-only integration with Operations Center
- Signed offline update bundle with rollback

---

## Important: NOT stable 1.1.0

This is a **test release candidate**. It is only available on the
`parity-test` channel. Stable channel users will not receive it.

---

## Exact Termux commands

Transfer the bundle to the phone, then run:

```bash
# Verify the candidate offline
hive update verify   ~/downloads/hive-1.1.0-rc.1-20260915-parity.tar.gz   --trust-store $HIVE_REPO_ROOT/updates/trust_store/hive-parity-test.pem   --platform termux   --architecture aarch64

# Inspect the plan
hive update plan   ~/downloads/hive-1.1.0-rc.1-20260915-parity.tar.gz

# Stage it
hive update stage   ~/downloads/hive-1.1.0-rc.1-20260915-parity.tar.gz   --release-root $HOME/Hive-Ops/data

# Activate (requires --approve)
hive install --activate $HOME/Hive-Ops/data/<release_id> --approve

# Or the combined apply form (same underlying engine)
hive update apply   ~/downloads/hive-1.1.0-rc.1-20260915-parity.tar.gz   --trust-store $HIVE_REPO_ROOT/updates/trust_store/hive-parity-test.pem   --release-root $HOME/Hive-Ops/data   --approve
```

After activation:

```bash
hive version
hive
hive net status
hive services status
hive health
hive doctor
hive audit
hive ps
hive logs status
hive speak
hive notes show
hive update status
hive install --status
```

Rollback:

```bash
hive install --rollback --approve
hive version
```

Re-apply:

```bash
hive update apply   ~/downloads/hive-1.1.0-rc.1-20260915-parity.tar.gz   --trust-store $HIVE_REPO_ROOT/updates/trust_store/hive-parity-test.pem   --release-root $HOME/Hive-Ops/data   --approve
```

---

## Trust store

The parity-test channel uses a dedicated key pair:

- Public key: `updates/trust_store/hive-parity-test.pem`
- Key ID: `hive-parity-test-2026-01`
- Fingerprint: `7ff51e2bb6dbc9de050f26a84aabe4998b357b02278acd406774e38bdfdb27d3`

The production key at `updates/trust_store/hive-release.pem` is untouched.

---

## Artifact

- Bundle: `release-output-parity-test/hive-1.1.0-rc.1-20260915-parity.tar.gz`
- Version: `1.1.0-rc.1`
- Release ID: `hive-1.1.0-rc.1-20260915-parity`
- Commit: `e9d342bf83629d1a964ccb81c5851dc5a9b9f39e`
- Channel: `parity-test`

---

## Website note

Source documentation is updated in `docs/`. Live GitHub Pages deployment for
this repo is currently limited to the `master` branch source; the
parity-test website section will be published through the existing Pages
workflow only after master is updated or a preview deployment is configured.
