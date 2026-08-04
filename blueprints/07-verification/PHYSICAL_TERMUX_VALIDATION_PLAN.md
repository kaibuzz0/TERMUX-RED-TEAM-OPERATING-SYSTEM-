# Physical Termux Validation Plan

## Required device

- Android 9+ device.
- Termux from F-Droid.
- Optional: Termux:Boot, Termux:API.

## Validation checklist

1. Install Hive OS via canonical installer.
2. Verify `~/.hive_auth/` is created with hashed credentials.
3. Reboot Termux and verify session gate triggers.
4. Open a second Termux session and confirm it bypasses the gate.
5. Run `hive status`, `hive doctor`, `hive system health`.
6. Create and enter a workspace.
7. Start and stop a managed service.
8. Run `hive network listeners` and verify loopback-only defaults.
9. Run `hive update stage` and `hive update apply`.
10. Run `hive recovery diagnose` and `hive recovery repair`.
11. Test `hive emergency-stop`.
12. Verify logs contain no secrets.
13. Verify battery/thermal impact after idle period.

## Exit criteria

- All tests pass or produce documented, accepted limitations.
- No runtime crash or data loss.
- Rollback path works.
