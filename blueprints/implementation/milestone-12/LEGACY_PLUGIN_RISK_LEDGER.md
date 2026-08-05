# Legacy Plugin Risk Ledger

## Hermes Plugins/hive-ops-plugin/

Status: **LEGACY / UNSAFE FOR BROKER INTEGRATION**

Not used by Milestone 12.

## Risk classification

- Broad routing by keyword patterns to arbitrary Hive components.
- Dangerous keywords (exfil, duress, self-destruct, c2).
- Direct execution intent via subprocess and shell-adjacent patterns.
- Service activation and network behavior suggested by component names.
- Secret access patterns implied by crypto/forensics routing.
- Unsafe intent inference from free-form text.
- Unsupported capabilities for a bounded broker.

## Action

Do not import, register, or activate this plugin in Milestone 12.
A future milestone may replace it with a manifest-driven broker client.
