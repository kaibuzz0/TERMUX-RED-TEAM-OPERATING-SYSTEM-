# Hive OS Vault Architecture

**Milestone 8**

## Scope

The Hive vault provides **application-level encrypted credential storage** for the Hive OS operator session gate and scoped service secrets.

It does **not** provide:

- Isolation from arbitrary malicious code under the same Termux UID.
- Replacement for Android device encryption (FBE).
- Replacement for Android lock-screen security.
- Protection while the vault is unlocked and secrets are in process memory.
- Kernel-level or hardware-backed secret isolation.

## Components

- `security/vault/crypto.py` — scrypt + HKDF-SHA256 + AES-256-GCM.

## Key hierarchy

```
master_material = scrypt(password, salt, scrypt_params)
encryption_key  = HKDF-SHA256(master_material, info="hive-vault-encryption-v1")
```

- scrypt provides the memory-hard password derivation.
- HKDF provides domain separation; the raw scrypt output is never used directly as an AES key.
- AES-GCM authenticates both the ciphertext and envelope security-critical metadata via AAD.
- `security/vault/format.py` — versioned vault envelope.
- `security/vault/storage.py` — atomic writes and containment checks.
- `security/vault/backend.py` — `Vault` API.
- `security/vault/session.py` — `VaultSession` lifecycle and bounded unlock attempts.
- `security/vault/migration.py` — legacy credential detection and migration planning.
- `security/vault/redaction.py` — secret redaction.
- `security/vault/cli.py` — `hive vault *` command surface.

## Envelope

```json
{
  "schema_version": 1,
  "kdf": {"name": "scrypt", "salt": "...", "parameters": {"n": ..., "r": 8, "p": 1}},
  "cipher": {"name": "AES-256-GCM", "nonce": "..."},
  "metadata": {"vault_id": "...", "created_at": "...", "updated_at": "..."},
  "ciphertext": "...",
  "authentication": "..."
}
```

## Storage location

Default: `$HOME/.hive/vault/vault.json`

- Restricted to private app storage.
- Atomic write via `vault.json.tmp` + `replace()`.
- No shared storage.
- Backup files stay encrypted.
