# Current Trust Boundaries

**Static model.** Effectiveness of boundaries is **UNVERIFIED ON TERMUX**.

## High-level boundaries

```text
+-------------------------------------------------------------+
| Android OS / Device                                         |
|  +-------------------------------------------------------+  |
|  | Termux application (single Android UID)              |  |
|  |  +-----------------------------------------------+   |  |
|  |  | Hive OS user-space scripts                    |   |  |
|  |  |  +-----------------------------------------+  |   |  |
|  |  |  | User files: ~/.hive_auth, ~/.bashrc    |  |   |  |
|  |  |  |                                          |  |   |  |
|  |  |  | Hive Ops Final/  Hive Ops DevAI/       |  |   |  |
|  |  |  | brain-plug/  Hermes Plugins/           |  |   |  |
|  |  |  +-----------------------------------------+  |   |  |
|  |  +-----------------------------------------------+   |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
```

## Boundary 1: Termux app sandbox

- All Hive files run inside the Termux app process.
- All files under Termux `$HOME` share the same Android application UID.
- There is **no kernel-level isolation** between Hive scripts and other Termux processes by default.
- This boundary is enforced by Android, not by Hive.

## Boundary 2: Unix permissions

- `~/.hive_auth/passwd` is `chmod 600`.
- Within the same UID, any process can read it.
- Cross-UID protection relies on Android; this is normal for Termux but not a strong vault.

## Boundary 3: Network modes

- `hive net off` claims fail-closed behavior.
- `hive net orbot` / `local` claim Tor routing.
- These are policy scripts, not kernel firewalls; enforcement depends on correct proxy configuration and application cooperation.

## Boundary 4: Secure login

- `hive-secure-login` is a shell prompt before launching the TUI.
- It does **not** prevent opening another Termux session (other sessions bypass the prompt).
- It is a session lock, not a device lock.
- It is **not** a replacement for Android lock screen, verified boot, or full-disk encryption.

## Boundary 5: Hermes plugin

- `Hermes Plugins/hive-ops-plugin/` is intended to bridge Hive and Hermes.
- Current code is a skeleton; whether it creates any additional trust boundary is **UNVERIFIED**.

## Boundary 6: Update / repair

- `update.sh` and `emergency-repair.sh` run with the user's Termux privileges.
- They download code from GitHub and execute it in place.
- There is no code-signing boundary or rollback boundary.

## Boundary 7: Root versus non-root

- Root scripts are not separated; the same files are used regardless of root status.
- Some scripts may assume root paths (`/root/hive` appears in `Hive Ops Final/bin/hive`).
- On non-root Termux, `/root/hive` is not writable; this is a **potential runtime failure**.

## Trust boundary diagram

See `blueprints/09-diagrams/trust-boundaries.mmd`.
