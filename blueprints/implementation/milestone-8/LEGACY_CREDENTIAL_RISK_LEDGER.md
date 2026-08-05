# HIVE OS Legacy Credential Risk Ledger

**Milestone 8**

| ID | File | Component | Credential type | Storage format | Status | Risk |
|----|------|-----------|-----------------|---------------|--------|------|
| R01 | `Hive Ops Final/bin/hive-secure-login` | session gate | operator password + PIN | base64 plaintext | active / legacy | **high** |
| R02 | `emergency-repair.sh` | recovery | `.hive_auth` directory | copied as-is | active / legacy | high (preserves R01) |
| R03 | `update.sh` | update | `.hive_auth` directory | copied as-is | active / legacy | high (preserves R01) |
| R04 | `.env` (referenced) | configuration | API keys / tokens | unknown | unknown | medium |
| R05 | `auth.json` (not found) | legacy | token / secret | JSON | legacy / unreachable | unknown |

## Risk taxonomy

- **High**: credential stored with reversible encoding, plaintext, or weak hash.
- **Medium**: credential in environment or subprocess without redaction.
- **Low**: test-only synthetic data, detection strings, or documentation.

## Mitigation plan

1. Implement encrypted vault (`security/vault/`) using mature cryptography.
2. Add migration adapter that detects `$HOME/.hive_auth/passwd` and produces a migration plan.
3. Do not modify `hive-secure-login` until the vault is proven on Termux.
4. After Termux validation, replace the base64 storage with vault-backed storage.
5. Update `emergency-repair.sh` and `update.sh` to preserve the vault file instead of the base64 file.
