# Install Test Matrix

| Scenario | Environment | Expected result |
|----------|-------------|-----------------|
| Clean install on Termux | Physical Android | `hive` command works, session gate configured, no errors in log |
| Reinstall over existing | Physical Android | Preserves config/vault/user data, updates runtime symlink |
| Dry-run install | Desktop Linux container | Shows planned changes without mutating system |
| Offline bundle install | Physical Android with bundle | Installs from verified bundle without network |
| Low-storage install | Emulator | Fails gracefully with clear message |
