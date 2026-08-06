# Policy Profiles

Built-in profiles:

- `observer` — read-only
- `operator` — read plus selected mutations with confirmation
- `administrator` — broader but still bounded
- `maintenance` — service and verified update maintenance
- `recovery` — recovery actions with strict verification
- `development` — development-only; never silently selected in production

Default profile: `observer`.

No profile grants arbitrary shell execution.
