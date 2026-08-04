# Legacy Installer Risk Ledger

**Milestone 6**

| Risk | `install.sh` | `install-termux.sh` | Severity | Notes |
|------|--------------|----------------------|----------|-------|
| Remote pipe execution in docs | line 6 | line 3 | High | README suggests `curl ... \| bash`; no verification |
| Unconditional package installation | line 103 | line 72 | High | `pkg install -y` with many packages |
| pip upgrade without isolation | line 107 | — | Medium | modifies user Python environment |
| Git clone from remote to `$HOME/hive` | line 121 | line 88 | High | no commit or source verification |
| Overwrites `.bashrc` and `.zshrc` | lines 202+ | — | High | appends exports unconditionally |
| Modifies Termux:Boot directory | lines 289+ | line 127 | High | writes boot scripts automatically |
| Creates symlinks into `$HOME/.local/bin` | lines 164, 167 | line 102 | Medium | may conflict with existing tools |
| No rollback mechanism | — | — | High | no staged install, no manifest |
| No source manifest or hash verification | — | — | High | cannot detect tampering |
| No preflight environment detection | minimal | minimal | Medium | only checks Termux version |
| No dry-run mode | — | — | High | always mutates immediately |
| No installation journal | — | — | High | cannot recover from partial failure |
| Installs from `Hive Ops DevAI/bin` | line 144 | line 95 | High | uses DevAI tree as source |
| Password/credential handling | — | line ~155 | High | `install-termux.sh` references password setup |
| Hardcoded install path | line 32 | line ~20 | Medium | `$HOME/hive` only; no override policy |

## Conclusion

Both legacy installers are:
- **Non-transactional**
- **Non-staged**
- **Immediately mutating**
- **Without source verification**
- **Without rollback**

They should be treated as legacy compatibility entrypoints only and replaced by the new `installer/` package once it passes physical Termux validation.
