# Context Trust Map

This document identifies the authoritative source for every trusted context value used by the Policy Engine.  Untrusted callers cannot directly assert safety-critical context.

| Context Field | Authoritative Source | Untrusted Assertion Handling |
|---|---|---|
| `configuration_profile` | `config_engine` | Broker normalizes via `config_engine.get_config("policy")`; raw value from caller is ignored. |
| `broker_policy_profile` | Broker policy bridge (`hive_broker/policy.py`) | Derived from config/profile_map; caller cannot override. |
| `runtime_mode` | Broker runtime state | Caller-provided value rejected; broker supplies `normal`/`bootstrap`/`recovery`. |
| `maintenance_mode` | Trusted state authority / broker runtime | Caller cannot assert `true`; only the trusted authority may set it. |
| `recovery_mode` | Trusted state authority / broker runtime | Same as maintenance_mode. |
| `vault_state` | Vault subsystem status adapter | Fabricated `UNLOCKED` is rejected; broker uses vault adapter status. |
| `rollback_available` | Update/recovery subsystem | Derived from recovery bundle inventory and rollback tests; not caller asserted. |
| `physical_validation_status` | Canonical release metadata/configuration | Caller-provided `VERIFIED` is rejected; only the release pipeline may mark verified. |
| `service_state` | Supervisor / service adapter | Broker reads from supervisor, not caller. |
| `update_verification_state` | Update subsystem verification adapter | Caller cannot assert verified. |
| `verified_bundle` | Update/recovery subsystem cryptographic verification | Must include evidence reference; raw `true` rejected. |
| `vault_unlocked` | Vault subsystem | Must be tied to a recent, bounded vault unlock event. |
| `operator_confirmation_state` | Broker approval store | Single-use, bound to transaction and capability; cannot be reused across transactions. |
| `manifest_digest` | Canonical release metadata | Supplied by broker from verified release manifest. |
| `transaction_id` | Broker transaction authority | Generated and bound by broker; decisions and audit use the same ID. |

## Rejection Rules

- Fabricated `vault_state: UNLOCKED` -> context validation fails or requirement unsatisfied -> DENY/DEFER.
- Fabricated `verified_bundle: true` -> requirement unsatisfied -> DEFER/DENY.
- Fabricated `physical_validation_status: VERIFIED` -> context validation fails or rule matches DEFER/DENY.
- Absent evidence is treated as `UNKNOWN` or triggers `DEFER`, never `ALLOW`.
- Freshness and evidence references are required for safety-relevant context.
