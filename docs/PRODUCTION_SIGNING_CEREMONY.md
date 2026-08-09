# Hive OS Production Signing Ceremony

## Scope

This document describes the planned procedure for producing a cryptographically signed Hive OS release artifact. It is a planning document only. No keys have been generated and no signing has been performed.

---

## Prerequisites

1. Owner-controlled offline environment (air-gapped or hardware-security-module)
2. Ed25519 key pair generated exclusively in that environment
3. Public key published to the Hive OS trust store
4. Private key never committed to, transmitted through, or stored in this repository

---

## Ceremony Steps

### 1. Generate Key Pair (offline)

Use a trusted Ed25519 implementation (e.g., OpenSSH, libsodium, or hardware token).

```
ssh-keygen -t ed25519 -C "hive-os-release@owner" -f hive-release-signing-key
```

The private key (`hive-release-signing-key`) stays offline.
The public key (`hive-release-signing-key.pub`) is the only item published.

### 2. Publish Public Key

Add the public key to:
- `updates/trust_store/` or equivalent offline trust-store distribution
- GitHub repository as a documented release-signing key
- Any out-of-band owner key registry

### 3. Build Final Artifact

Use the Release Engine builder on a clean checkout of the final 1.0.0 tag:

```
python -m release_engine.cli build \
  --source . \
  --output ./dist \
  --version 1.0.0 \
  --sequence <final_sequence> \
  --revision <final_commit_sha>
```

### 4. Calculate Digests

Record:
- artifact SHA-256
- manifest digest (SHA-256 of canonical manifest JSON)
- metadata canonical JSON digest

### 5. Sign Metadata Offline

Transfer only the `metadata.json` file to the offline signing environment.

Sign the canonical JSON digest with the Ed25519 private key.

Return only the signature and key ID to the online environment.

### 6. Attach Signature

Inject the signature into the release metadata:

```json
{
  "signing": {
    "algorithm": "Ed25519",
    "key_id": "<key_identifier>",
    "signature": "<base64_signature>"
  }
}
```

### 7. Verify Using Public Trust Store

Run:

```
python -m release_engine.cli verify \
  <artifact.tar.gz> \
  --trust-store <trust_store.pem> \
  --current-sequence <prior_sequence>
```

Require: verified = True

### 8. Tamper Test

- Modify one byte in the archive; verify rejection
- Modify manifest digest in metadata; verify rejection
- Use wrong public key; verify rejection
- Roll back sequence number; verify rejection

### 9. Record Key ID

Document the signing key identifier in:
- release notes
- `docs/PRODUCTION_SIGNING_CEREMONY.md` execution log
- out-of-band owner registry

### 10. Publish Only Verified Artifact

Never publish an artifact that has not passed steps 7 and 8.

---

## Emergency Key Revocation

If the private key is compromised or suspected compromised:

1. Generate a new Ed25519 key pair offline
2. Publish revocation notice with:
   - revoked key ID
   - revocation sequence number (must be > all prior)
   - new replacement key ID
   - owner attestation (signed by replacement key or out-of-band)
3. Update trust store to reject the revoked key
4. Re-sign any affected release metadata with the new key
5. Re-verify all published artifacts

---

## Current Status

| Step | Status |
|------|--------|
| Key pair generated | NOT YET |
| Public key published | NOT YET |
| Artifact built | NOT YET (RC built, not signed) |
| Signature attached | NOT YET |
| Verification passed | NOT YET |
| Tamper test passed | NOT YET |
| Key ID recorded | NOT YET |

---

*Planning document: 2026-08-09*
*Signing ceremony: pending owner approval and offline key generation*
