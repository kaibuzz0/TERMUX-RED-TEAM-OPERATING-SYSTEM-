# Vault Specification

## Scope

The vault provides application-level encrypted secret storage. It protects secrets at rest. The blueprint acknowledges realistic limitations:

- Secrets become accessible while the vault is unlocked.
- Same-UID malicious code may potentially access unlocked material.
- Android device security remains important.
- Application-level encryption does not replace Android full-device protection.
- Environment variables can leak through subprocesses and logs.

## Design

### Encryption

- Algorithm: AES-256-GCM or ChaCha20-Poly1305 via Python `cryptography`.
- KDF: Argon2id if available, else PBKDF2-HMAC-SHA256 with high iteration count.
- Salt: 16+ bytes generated per vault file, stored alongside the ciphertext.
- Work factor: tunable; default calibrated for ~500 ms on target ARM64 device.
- Authenticated encryption detects tampering and corruption.

### Storage

- Location: `~/.local/share/hive/vault/`.
- Format: versioned JSON or msgpack with encrypted blobs.
- Atomic writes: write to temp file, fsync, rename.
- Corruption detection: HMAC/AEAD tag verification on load.

### Unlock

- Requires operator passphrase.
- Optional: hardware-bound token (e.g., Android Keystore via Termux:API if available).
- Derived key is held in memory only while vault is unlocked.
- Auto-lock after configurable idle timeout.

### Secret scoping

- Each secret has a scope (e.g., `work/dev-signing`, `work/ssh-key`, `personal/vault`).
- Agents receive a capability referencing a scope, not the secret itself.
- Broker returns signatures or scoped tokens derived from the secret.

### Subprocess secret delivery

- Prefer passing secrets via inherited file descriptors or temporary files with tight permissions.
- Avoid environment variables for high-value secrets.
- Wipe temporary files immediately after use.

### Clipboard

- Never place high-value secrets on the clipboard by default.
- If clipboard use is allowed, set a short timeout and clear it.

### Backup

- Vault files may be backed up only if encrypted.
- Plaintext exports require explicit operator confirmation.

### Rotation

- Support re-encryption with a new passphrase.
- Support migration to a new KDF version.

### Threat limitations

- Unlocked vault material is vulnerable to same-UID malware.
- Memory dump attacks on a rooted device can expose derived keys.
- The vault does not protect against a compromised kernel.

These limitations are documented, not hidden.

## Implementation note

Do not implement custom cryptography. Use mature libraries. Verify Termux support for chosen library before first release.
