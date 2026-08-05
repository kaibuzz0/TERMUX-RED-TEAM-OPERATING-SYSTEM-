# Hive OS Security Boundaries

**Milestone 8**

## Accurate claims

- The Hive vault is **application-level encrypted credential storage**.
- It protects secrets **at rest** when the vault is locked.
- It uses mature, well-reviewed cryptography (`cryptography` library, AES-256-GCM, scrypt, HKDF-SHA256).

## Non-claims

The Hive vault does **not**:

- Provide hardware-backed key storage.
- Replace Android lock-screen security.
- Bypass or modify Android SELinux / verified boot / system partitions.
- Protect secrets from a fully compromised Termux application process while the vault is unlocked.
- Guarantee memory erasure in Python.

## Terminology

Use:

- Hive vault
- Hive operator session gate
- Application-level encrypted credential storage

Avoid:

- unbreakable
- military-grade
- hardware vault
- secure boot credential
- full-device protection
