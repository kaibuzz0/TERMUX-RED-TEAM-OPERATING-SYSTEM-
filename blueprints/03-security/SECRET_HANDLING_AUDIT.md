# Secret Handling Audit

## Locations searched

Static scan of all text files for: `base64`, `passwd`, `password`, `pin`, `token`, `secret`, `.env`, `auth.json`.

## Findings

| Path | Secret-related behavior | Assessment |
|------|------------------------|------------|
| `install-termux.sh` | Prompts password+PIN, writes `printf '%s
%s' "$PASS1" "$PIN1" | base64 > "$AUTH_DIR/passwd"` | **CRITICAL**: reversible encoding, not encryption or hashing |
| `emergency-repair.sh` | Nuke mode prompts new password+PIN and writes them the same base64 way | **CRITICAL**: same weakness |
| `Hive Ops Final/bin/hive-secure-login` | Reads `~/.hive_auth/passwd`, base64-decodes, compares against entered password+PIN | Stores and compares plaintext-equivalent values |
| `README.md` | Claims "Credentials stored base64-encoded (file is chmod 600)" under an "Encryption" table header | **MISLEADING**: base64 is not encryption |
| `update.sh` | Backs up `~/.hive_auth` directory during updates | Backup copies credential file verbatim |
| `emergency-repair.sh` | Copies `~/.hive_auth` to `~/.hive_rescue/` | Rescue directory contains plaintext-equivalent credentials |
| `install.sh` | Sets `HERMES_HIVE_MODE` and `HERMES_HIVE_BRIDGE` env vars; no API keys stored | Low risk |
| `Hermes Plugins/install.sh` | No observed secret handling | N/A |
| `requirements.txt` | Lists `bcrypt`, `cryptography`, `pynacl`; these are available but not used for the login credential | **GAPPED**: crypto libraries present but not applied |

## Base64 vs encryption vs hashing

- **Base64:** reversible encoding; trivial to decode. **Not a security control.**
- **Encryption:** reversible with a key. Requires key management.
- **Hashing (slow + salted):** one-way. Correct approach for password verification.

Current code uses base64. It does not use `bcrypt`, `cryptography`, or `pynacl` for the login credential, despite those libraries being in `requirements.txt`.

## Secret lifecycle

1. User enters password+PIN.
2. Installer concatenates them with a newline.
3. Installer base64-encodes the result.
4. Result stored in `~/.hive_auth/passwd` with mode 600.
5. `hive-secure-login` base64-decodes the file and compares to entered values.
6. `update.sh` and `emergency-repair.sh` copy this file during backups/rescue.

## Exposure vectors

- Any process sharing the Termux application UID can read the file.
- Backup/rescue copies remain after recovery.
- No forward-secrecy or rotation.
- Log file `~/.hive_auth/login.log` may capture entered values or timing; not inspected yet.

## Required remediation

- Replace base64 storage with `bcrypt` or `argon2` salted hash of password+PIN.
- Store salt separately or prefixed.
- Do not store PIN in reversible form.
- Remove "Encryption" claim from README and use "encoding" or "hash" accurately.
- Encrypt backups/rescue if credentials are included.
- Add login-log redaction policy.

## Credential locations summary

| File | Contents | Sensitivity |
|------|----------|-------------|
| `~/.hive_auth/passwd` | base64(password + newline + PIN) | **CRITICAL** |
| `~/.hive_auth/login.log` | Login attempts/timestamps | **HIGH** |
| `~/.hive_backup/<ts>/.hive_auth/passwd` | Copy of credential file | **CRITICAL** |
| `~/.hive_rescue/.hive_auth/passwd` | Copy of credential file | **CRITICAL** |
