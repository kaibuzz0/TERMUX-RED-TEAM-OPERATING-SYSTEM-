# Milestone 7 Physical Termux Validation Plan

1. Install Termux on an isolated Android device or emulator.
2. Clone the repository into Termux private storage.
3. Run:
   - `python3 -m installer.install --check`
   - `python3 -m installer.install --plan`
   - `python3 -m installer.install --dry-run`
   - `python3 -m installer.install --stage`
   - `python3 -m installer.install --verify <staged>`
   - `python3 -m installer.install --activate <staged> --approve`
   - `python3 -m installer.install --status`
   - `python3 -m installer.install --rollback --approve`
4. Verify:
   - `active.json` points to a release under `$HOME/.local/share/hive`.
   - No `.bashrc` change.
   - No Termux:Boot change.
   - No package installation beyond what the user already chose.
   - No listener or service.
5. Create an interruption at pointer switch and confirm recovery.

Status: **NOT YET RUN**.
