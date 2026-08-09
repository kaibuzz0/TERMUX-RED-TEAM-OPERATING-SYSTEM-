"""Bootstrap and Emergency Compromise Policy for Hive OS Trust Anchor.

## 1. BOOTSTRAP POLICY: "Who authenticates the trust store itself?"

Answer: The trust store is authenticated by the SOFTWARE PACKAGING CHAIN and
by OUT-OF-BAND VERIFICATION, not by a self-referential signature.

### 1.1 Initial Trust Establishment

1. The Hive OS source code repository is the canonical authority.
2. The production trust-store file is:
       updates/trust_store/hive-release.pem
3. This file is committed to the repository and protected by the same
   access controls as the source code (GPG-signed commits, branch protection,
   mandatory code review, CI checks).
4. The trust store does NOT sign itself. It is a plaintext PEM file with
   metadata comments. Its authenticity is derived from repository integrity.
5. On first install, the trust-store file is copied into the runtime
   environment as part of the installation bundle.

The initial trusted production release public key is distributed with the
Hive source / release package. It is bound to:

- key_id: human-readable identifier (e.g. hive-release-prod-2026-01)
- Ed25519 public key (SubjectPublicKeyInfo PEM)
- pinned SHA-256 fingerprint (computed over raw 32-byte Ed25519 public key)
- purpose: release

The fingerprint SHOULD be independently published and verified through an
out-of-band channel (project website, signed email, hardware token attestation)
where practical.

Release verification subsequently uses that pinned trust anchor.

### 1.2 EMBEDDED INSTALLER BOOTSTRAP KEY

**STATUS: NOT IMPLEMENTED**

There is currently NO embedded bootstrap public key in the installer binary.

A future design may embed a single Ed25519 bootstrap public key in the
installer to verify the initial release bundle independently of the
source-code repository, but that mechanism does not exist in Hive OS 1.0.

Do not rely on documentation that claims otherwise.

### 1.3 Trust Store Update Path

- New trust-store releases are delivered as signed update bundles.
- The bundle is signed by a key currently in the active trust store.
- The bundle contains the replacement trust-store file.
- The verifier checks the bundle signature, then replaces the trust store.
- Anti-rollback prevents downgrading to a revoked trust-store version.

### 1.4 Chain of Trust Summary (Actual Model)

    Hive source / release package (with pinned trust anchor)
         |
         +---> Trust store T1 (production key A)
         |
         v
    Signed release bundle v1.1.0
         |
         +---> Trust store T2 (production key A + key B)
         |
         v
    Signed release bundle v2.0.0
         |
         +---> Trust store T3 (revoked A, active B + key C)

At no point does the trust store sign itself. Each transition is signed
by a key already present in the PREVIOUS trust store.

---

## 2. EMERGENCY COMPROMISE PROCEDURE

### 2.1 Detection

Suspected compromise indicators:
- Unauthorized release signed with a production key
- Private key material suspected exfiltrated
- Anomalous CI/CD pipeline activity
- Insider threat or infrastructure breach

### 2.2 Immediate Response (0–30 minutes)

1. **HALT** all signed releases. Stop CI/CD pipelines.
2. **REVOKE** the compromised key fingerprint in the trust store
   using `TrustStore.revoke_key(key_id, replacement_key_id)`.
3. **INVALIDATE** all releases signed with the compromised key
   by adding their release sequences to the revoked-sequences set.

### 2.3 Replacement Key Generation (offline)

1. Generate a new Ed25519 key pair on an air-gapped machine.
2. Encrypt the private key with a strong passphrase
   (PKCS#8 `BestAvailableEncryption` or OpenSSH format).
3. Compute the SHA-256 fingerprint of the raw public key.
4. Export the public key PEM with `export_public_key_pem()`.
5. Print the fingerprint and key_id on paper.
6. Store the encrypted private key on offline encrypted media
   (hardware token, encrypted USB drive, or HSM).
7. **NEVER** commit the private key to any repository or network storage.

### 2.4 Trust-Store Update

1. Add the new public key PEM to `updates/trust_store/hive-release.pem`.
2. Mark the compromised key as `revoked` with the new key as `replacement_key_id`.
3. Update `trusted_keys.json` (if present) with the new key status.
4. Sign the updated trust-store file with a still-trusted key.
5. Commit the updated trust-store file to the repository with
   GPG-signed commit and mandatory code review.
6. CI must pass the full test suite including M20/M20.1 tests.

### 2.5 Distribution of Replacement Trust Anchor

1. Publish the new trust-store fingerprint through an independent
   out-of-band channel (project website, signed email, social media,
   hardware security module attestation).
2. Users verify the fingerprint independently before accepting updates.
3. The updated trust-store file is shipped in the next signed release bundle.

### 2.6 Invalidation of Affected Releases

1. All releases signed with the compromised key are revoked.
2. Add their release sequences to the revoked-sequences list.
3. Publish a security advisory with affected release IDs and fingerprints.
4. Users with affected releases MUST reinstall from a verified earlier
   release or from the new signed release.

### 2.7 Post-Incident Verification

1. Audit all CI/CD logs for unauthorized signing events.
2. Verify that the compromised key is not present in any active
   trust stores, CI secrets, or runtime environments.
3. Rotate all CI/CD credentials and access tokens.
4. Document the incident and publish a post-mortem.

---

## 3. KEY FORMATS AND LOADING

### 3.1 Private Key Formats

| Format | Loading Function | Notes |
|--------|------------------|-------|
| PKCS#8 PEM | `load_pem_private_key()` | Standard; supports encryption |
| OpenSSH | `load_ssh_private_key()` | Requires conversion for some tools |

Both are supported by the Hive OS signing tools. Production keys MUST
be encrypted at rest.

### 3.2 Public Key Format

- SubjectPublicKeyInfo PEM with metadata comments.
- Fingerprint: SHA-256 over raw Ed25519 public key bytes (32 bytes).

### 3.3 Trust-Store File Format

Plaintext PEM file with one or more blocks:

    # key_id: hive-release-prod-2026-01
    # fingerprint_sha256: abc123...
    # purpose: release
    -----BEGIN PUBLIC KEY-----
    ...
    -----END PUBLIC KEY-----

No JSON, no binary encoding, no signature over the file itself.

---

## 4. TRUST-STORE LOCATION

Canonical production trust-store file:

    updates/trust_store/hive-release.pem

This path is:
- Stored in the repository
- Referenced by `updates.trust.TRUST_STORE_PATH`
- Shipped with every release bundle
- Loaded at runtime by `TrustStore.from_pem_file(TRUST_STORE_PATH)`

No other path is authoritative for production releases.
