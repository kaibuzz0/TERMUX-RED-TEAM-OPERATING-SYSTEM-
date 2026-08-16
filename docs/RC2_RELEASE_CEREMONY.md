# Hive RC.2 Release Ceremony

This document is the release gate for the V2 clean-install path. It is intentionally split so the production private signing key never enters GitHub Actions, the repository, or the runtime bundle.

## Invariants

- `master` is not a candidate build workspace.
- A candidate is built from one exact commit SHA.
- Candidate creation is unsigned and reproducible.
- The production private key is used only in the offline signing environment.
- Signing a metadata sidecar is **not** enough: the signed metadata must be sealed back into the exact `.tar.gz` that will be published.
- The standalone bootstrap verifies the sealed bundle before any Hive code from that bundle is executed.
- A security sequence must not be reused for a different release identity. Exact same-release replay at the same sequence is allowed; a different release requires a new sequence.
- Publication and website installer changes happen only after physical Termux validation.

## Gate 1 — Green source revision

Use the exact V2 branch commit that has passed the full GitHub matrix and security gate. Record the commit SHA before building.

Do not build a release candidate from a dirty working tree or from an unreviewed local patch.

## Gate 2 — Build the unsigned candidate

Run the GitHub Actions workflow **Build Hive RC.2 Candidate** on the selected V2 revision.

Inputs:

- version: normally `1.1.0-rc.2`
- security sequence: the new monotonic sequence chosen for this release identity

The workflow:

1. pins `SOURCE_DATE_EPOCH` to the source commit timestamp;
2. builds the candidate twice outside the repository tree;
3. requires byte-for-byte equality of bundle, manifest, and metadata;
4. verifies required runtime/installer files are present;
5. checks manifest closure and source-revision binding;
6. creates a standalone `hive-bootstrap.pyz`;
7. uploads an **unsigned** candidate kit only.

The artifact contains no private key and is not publishable yet.

## Gate 3 — Inspect the signing kit

Before signing, verify the artifact checksums and inspect `CANDIDATE.json`, the metadata sidecar, and the manifest.

Required metadata properties include:

- expected release version;
- expected source commit;
- `platforms = ["termux"]`;
- `architectures = ["aarch64"]`;
- correct `security_sequence`;
- empty signature block before signing;
- expected production key id recorded by the candidate kit: `hive-release-prod-2026-02`.

If any identity field is wrong, discard the candidate and rebuild. Do not edit signed fields by hand.

## Gate 4 — Offline production signing

Move only the unsigned metadata sidecar into the offline signing environment. The private key remains there.

Example command shape:

```bash
python -m release_engine.cli sign \
  --metadata hive-os-1.1.0-rc.2-<build>.metadata.json \
  --private-key /secure/offline/production-release-key.pem \
  --key-id hive-release-prod-2026-02 \
  --output metadata.signed.json
```

The path above is illustrative. Never place a production private key inside the repository, GitHub Actions secrets for this workflow, a release asset, or a Termux runtime.

After signing, the private key stays offline. Only `metadata.signed.json` leaves the signing environment.

## Gate 5 — Seal the publishable bundle

Signing the sidecar does not modify the candidate tarball. Seal the signed metadata into the exact candidate bundle:

```bash
python -m release_engine.cli seal \
  --bundle hive-os-1.1.0-rc.2-<build>.tar.gz \
  --signed-metadata metadata.signed.json \
  --output hive-os-1.1.0-rc.2-<build>.signed.tar.gz
```

The sealer refuses:

- unsigned metadata;
- a different release identity;
- a different unsigned metadata payload;
- a manifest digest that does not match the candidate bundle.

Generate and record the SHA-256 of the sealed bundle.

## Gate 6 — Standalone bootstrap verification

Verify the exact sealed artifact with the standalone bootstrap before publication:

```bash
python hive-bootstrap.pyz verify \
  hive-os-1.1.0-rc.2-<build>.signed.tar.gz \
  --platform termux \
  --architecture aarch64 \
  --current-sequence <CURRENT_SEQUENCE> \
  --current-release-id <CURRENT_RELEASE_ID> \
  --json
```

For a genuinely empty installation there is no current release identity, so the current sequence is `0` and `--current-release-id` is omitted.

A failed signature, wrong key id, wrong platform/architecture, rollback sequence, equal-sequence identity conflict, manifest mismatch, unsafe archive member, unsigned extra file, wrong file size, or wrong SHA-256 is a release stop.

## Gate 7 — Physical clean-Termux staging

On a disposable/fresh Termux environment:

1. install only the bootstrap prerequisites;
2. run the standalone bootstrap artifact rather than cloning Hive;
3. download the exact sealed candidate over HTTPS;
4. run without `--approve` first;
5. confirm verification succeeds and the release reaches `ready_to_activate` without replacing the active runtime.

Record device architecture, Termux/Python/cryptography versions, candidate SHA-256, release ID, sequence, and command output.

## Gate 8 — Physical activation

Only after the staging result is inspected, repeat with explicit `--approve`.

Validate all of the following:

- versioned active runtime exists under the Hive data root;
- `active.json` points to that exact runtime;
- the managed global `hive` command exists and launches the active release;
- Termux autoboot is installed once and is idempotent;
- `hive --help`, `hive version`, and a basic status/doctor path execute successfully.

## Gate 9 — Update, rollback, recovery

Before calling RC.2 complete, prove the lifecycle rather than only first install:

1. install/activate release A;
2. stage and activate newer signed release B;
3. verify the global launcher follows B;
4. roll back to A and verify the same global launcher follows A without being rewritten;
5. reject an older security sequence;
6. reject an equal sequence bound to a different release ID;
7. reject a corrupted/tampered bundle;
8. prove a failed candidate does not destroy the last known-good active runtime.

## Gate 10 — Publication

Only after all earlier gates pass:

- create the RC.2 prerelease;
- upload the **sealed** signed bundle and its public metadata/checksums;
- verify the published asset digest matches the physically tested artifact;
- update the website/bootstrap install command to that exact release asset;
- keep stable/V2 promotion separate from RC.2 publication.

The artifact that was verified and physically tested must be the artifact that is published. Rebuilding after validation creates a different candidate and restarts the release gates.
