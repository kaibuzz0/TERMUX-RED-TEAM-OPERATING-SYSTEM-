# Hive OS 1.0.0

Hive OS is a secure, compartmentalized operating environment for Android, Termux-PROot, and Linux shell environments. It provides:

- A default-deny policy engine and capability broker
- Encrypted local vault for credentials and secrets
- Signed offline release/update lifecycle
- Service orchestration with dependency validation
- Plugin SDK with manifest-based, opt-in execution

This is the stable 1.0.0 release.

## Current Release

| Field | Value |
|---|---|
| Product | Hive OS |
| Version | `1.0.0` |
| Git tag | [`hive-os-v1.0.0`](https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-/releases/tag/hive-os-v1.0.0) |
| Source revision | `de5ebe4ae9fd340331b796a67e70d484cd13e7d8` |
| Release sequence | `20` |
| Channel | `stable` |
| Reproducibility | CONTENT_REPRODUCIBLE |

> **Note:** The historical Git tag `v1.0.0` points to an unrelated earlier commit and was not modified. Use `hive-os-v1.0.0` as the canonical Hive OS stable tag.

## CURRENT MASTER / 1.0.1 REPAIR

The `master` branch contains dependency-split and Termux-native install fixes not yet in the `hive-os-v1.0.0` stable tag. Until `hive-os-v1.0.1` is formally tagged, use `master` for native Termux installation.

Dependency files:
- `requirements-runtime.txt` — minimal core runtime (pyyaml, cryptography)
- `requirements-extras.txt` — optional legacy / AI / networking
- `requirements-dev.txt` — pytest, black, flake8, mypy
- `requirements.txt` — preserved historical full dependency set

### A. Termux (Normal User Install — CURRENT MASTER / 1.0.1 REPAIR)

Requires Termux from F-Droid. Run the easy installer once; it installs Hive OS as
a real environment with a global `hive` command and Termux autoboot.

```bash
pkg update
pkg install -y curl git python python-cryptography

bash -c "$(curl -fsSL https://raw.githubusercontent.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-/master/install-termux-easy.sh)"
```

After installation:

- Type `hive` anywhere to launch Hive OS.
- Open a **new** Termux session and Hive OS boots automatically.
- Exit Hive to return to the normal Termux shell.
- Disable autoboot: `hive autoboot disable`
- Re-enable autoboot: `hive autoboot enable`

Optional extras (legacy AI/network tools):
```bash
python -m pip install -r requirements-extras.txt
```

#### Manual / developer source run

If you prefer not to install a global command, you can run directly from the
cloned repository:

```bash
pkg update
pkg install -y git python python-cryptography

git clone --depth 1 --branch master https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git ~/Hive-Ops
cd ~/Hive-Ops

python -m pip install -r requirements-runtime.txt

python bin/hive --help
python bin/hive broker capabilities
python bin/hive config validate
```

To inspect the safe transactional installer plan:

```bash
python -m installer.install check
python -m installer.install plan
python -m installer.install dry-run
```

> `install.sh` and `install-termux.sh` are legacy, non-transactional scripts. They are disabled by default and require `HIVE_LEGACY_UNSAFE=1` to run. Prefer the easy installer or the safe installer workflow above.

### B. Linux Shell (Full Supported Runtime)

```bash
# Ensure Python 3 and python3-cryptography are installed via your package manager

git clone --depth 1 --branch master https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git ~/Hive-Ops
cd ~/Hive-Ops

python3 -m pip install -r requirements-runtime.txt

python3 bin/hive --help
python3 bin/hive broker capabilities
python3 bin/hive config validate
```

Optional extras:
```bash
python3 -m pip install -r requirements-extras.txt
```

### C. Windows Command Prompt (Development / Portable Run)

Hive OS is primarily designed for Android/Termux/Linux. Windows is supported only as a development and portable testing environment.

```cmd
git clone --depth 1 --branch master https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git
cd TERMUX-RED-TEAM-OPERATING-SYSTEM-

python -m pip install -r requirements-runtime.txt

python bin\hive --help
python bin\hive broker capabilities
python bin\hive config validate
```

Optional extras:
```cmd
python -m pip install -r requirements-extras.txt
```

If `python` is not on your PATH, use:

```cmd
py -3 bin\hive --help
```

### D. Windows PowerShell (Development / Portable Run)

```powershell
git clone --depth 1 --branch master https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git
cd TERMUX-RED-TEAM-OPERATING-SYSTEM-

python -m pip install -r requirements-runtime.txt

python .\bin\hive --help
python .\bin\hive broker capabilities
python .\bin\hive config validate
```

Optional extras:
```powershell
python -m pip install -r requirements-extras.txt
```

## Verified Offline Install (Advanced)

Download the signed release bundle from the [`hive-os-v1.0.0` GitHub Release](https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-/releases/tag/hive-os-v1.0.0), then verify and inspect it with the Release Engine:

```bash
python -m release_engine.cli verify hive-os-1.0.0-release.tar.gz   --trust-store updates/trust_store/hive-release.pem

python -m release_engine.cli inspect hive-os-1.0.0-release.tar.gz
```

## Verify Installation

Run these commands after cloning to confirm the system resolves and responds:

```text
python bin/hive --help
python bin/hive --resolve
python bin/hive --runtime-info --json
python bin/hive config validate
python bin/hive broker capabilities
python bin/hive broker status
python bin/hive update status
python bin/hive release version
python bin/hive ops
```

## Security

- Release metadata is signed with Ed25519.
- Active production key: `hive-release-prod-2026-03`
- Revoked key: `hive-release-prod-2026-01`
- Trust anchor: `updates/trust_store/hive-release.pem`
- Local secrets live in an encrypted vault.
- Default-deny policy is enforced by the broker.
- Plugins are disabled by default and require explicit opt-in; arbitrary plugin execution is not supported.

## Supported / Validated Platforms

| Platform | Status |
|---|---|
| Android / aarch64 | validated |
| Termux-PROot | validated |
| Linux CI | validated via GitHub Actions |
| Native Termux | not fully physically validated |
| Windows | development / portable testing environment only |

## Download / Release

- Release: https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-/releases/tag/hive-os-v1.0.0
- Tag: `hive-os-v1.0.0`
- Historical unrelated tag: `v1.0.0` (not the canonical stable release)
