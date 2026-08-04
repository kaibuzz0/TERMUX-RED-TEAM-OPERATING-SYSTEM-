# Attack Surface

**Static model.** Actual exploitability is **UNVERIFIED ON TERMUX**.

## Network attack surface

| Surface | Entry point | Current control | Risk |
|---------|-------------|---------------|------|
| GitHub clone/pull | `install-termux.sh`, `update.sh`, `emergency-repair.sh` | TLS only | HIGH |
| Termux package repos | `pkg install` | TLS + trust in Termux/F-Droid | MEDIUM |
| PyPI | `pip install -r requirements.txt` | TLS + loose pins | HIGH |
| Orbot/Tor control | `hive net orbot` | External app | MEDIUM |
| Local Tor listener | `hive net local` | 127.0.0.1:9052 (claimed) | MEDIUM |
| HTTP/Flask services in tools | `brain-plug/therapist_code only.py`, some DevAI tools | Unknown | MEDIUM |
| Any `0.0.0.0` binding | tools with listener strings | Unknown | HIGH |

## Local attack surface

| Surface | Entry point | Current control | Risk |
|---------|-------------|---------------|------|
| `~/.hive_auth/passwd` | any Termux UID process | chmod 600 | HIGH |
| `~/.hive_backup/` | any Termux UID process | directory permissions | MEDIUM |
| `~/.hive_rescue/` | any Termux UID process | directory permissions | MEDIUM |
| `~/.bashrc` | any Termux UID process | user-owned | LOW |
| `~/.termux/boot/` | any Termux UID process | user-owned | MEDIUM |
| `~/bin/hive*` symlinks | any Termux UID process | user-owned | LOW |

## Supply-chain attack surface

| Surface | Entry point | Current control | Risk |
|---------|-------------|---------------|------|
| GitHub repo compromise | all remote install/update/repair | TLS only | HIGH |
| PyPI dependency substitution | `requirements.txt` | loose pins | HIGH |
| Termux package substitution | `pkg install` | trust in repo | MEDIUM |
| Malicious `.git` hooks/scripts | cloned repo | none beyond HTTPS | MEDIUM |

## Human / operator attack surface

| Surface | Entry point | Current control | Risk |
|---------|-------------|---------------|------|
| README recommends `curl ... | bash` | social engineering | none | HIGH |
| `--full-nuke` confirmation bug | operator error | possibly broken confirmation | HIGH |
| `--force` stashes local changes | operator error | warning only | MEDIUM |
| Unbounded agent delegation | operator trusts AI | none | HIGH |
| False "secure boot" claims | operator over-trust | none | MEDIUM |

## Largest attack-surface items

1. Remote-script execution (`curl | bash`) in README and installer docs.
2. Unverified GitHub/PyPI downloads.
3. Base64 credential storage.
4. Unbounded recursive agent orchestrator.
5. Unquoted destructive paths.
