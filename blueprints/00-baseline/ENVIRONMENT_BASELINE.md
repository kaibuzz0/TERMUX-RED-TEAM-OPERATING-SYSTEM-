# Environment Baseline

**Host operating system:** Windows 10 (AMD64)
**Python runtime:** 3.11.15 (main, Jun  2 2026, 22:29:49) [MSC v.1944 64 bit (AMD64)]
**Current Hermes working directory:** `E:/Hermes-USB-Portable-main/src/hermes-agent`
**Hive OS repository root:** `E:/Hermes-USB-Portable-main/TERMUX-RED-TEAM-OPERATING-SYSTEM-`
**Git binary used:** `E:/Hermes-USB-Portable-main/.cache/runtimes/windows-x64/git/cmd/git.exe` (version 2.54.0.windows.1)
**Shell availability:** Git Bash is **not** available on this Windows host; native `terminal`, `search_files`, and `read_file` tools fail with `Git Bash not found`.
**Fallback inspection method:** `execute_code` with Python `pathlib`/`subprocess` using the bundled Git binary.

## Missing Termux / Android capabilities

- `pkg` package manager — unavailable.
- `termux-api` and Android API bindings — unavailable.
- `termux-setup-storage` — unavailable.
- Termux:Boot execution environment — unavailable.
- Android application UID, SELinux, and verified-boot context — unavailable.
- Linux kernel namespaces, seccomp, Landlock in Termux configuration — unavailable.
- `/data/data/com.termux/files/usr/bin/bash` shebangs are statically readable but not executable here.

## Static-analysis limitations

- Can verify file existence, size, shebang, extension, and text content.
- Can extract command lists and control-flow from source.
- **Cannot** execute Termux scripts.
- **CANNOT** verify runtime behavior, package installation, boot integration, network listeners, or Android APIs.
- **CANNOT** confirm that a displayed menu actually renders on Termux.
- **CANNOT** confirm that `hive-secure-login` actually blocks access or that credentials are verified correctly.
- **CANNOT** confirm that `hive` subprocess calls succeed on Termux.

## Runtime claim classification

| Claim | Verification status |
|-------|---------------------|
| File inventory and paths | STATICALLY VERIFIED |
| Git metadata (remote, branch, HEAD) | VERIFIED ON WINDOWS HOST |
| Script syntax where parseable | STATICALLY VERIFIED |
| Termux package installation behavior | UNVERIFIED ON TERMUX |
| Hive session gate script execution | UNVERIFIED ON TERMUX |
| Hive managed-session lock behavior | UNVERIFIED ON TERMUX |
| `hive` CLI subcommand execution | UNVERIFIED ON TERMUX |
| TUI rendering | UNVERIFIED ON TERMUX |
| Network mode switching (orbot/local/off) | REQUIRES PHYSICAL ANDROID TEST |
| Root-enhanced features | REQUIRES ROOTED-ANDROID TEST |
| Android API integration | REQUIRES PHYSICAL ANDROID TEST |
| Hermes plugin registration at runtime | UNVERIFIED ON TERMUX |

## Exact requirements for later Android validation

1. Execute `bash install-termux.sh` on a clean Termux install and capture `hive_install.log`.
2. Reboot Termux (or run `~/.termux/boot/00-hive-secure.sh`) and verify login prompt.
3. Run `hive status`, `hive health`, `hive net status`, `hive dashboard` and capture outputs.
4. Run `bash update.sh` and `bash emergency-repair.sh` on a modified install.
5. Verify that `~/.hive_auth/passwd` is created and its contents are base64.
6. Check `~/.bashrc` modifications and `~/bin` symlinks.
7. Run `bandit` and `pytest` from the CI workflow on an Ubuntu host for the `Hive Ops DevAI` tree.
8. Physical device must have Termux from F-Droid and, optionally, Termux:Boot app.
