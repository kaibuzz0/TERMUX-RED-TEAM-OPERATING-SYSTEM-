# Decision-to-Enforcement Matrix

The Hive Broker treats every Policy Engine decision state exactly as follows.  No state is reinterpreted.

| Decision | Dispatch | Return to Caller | Approval | Requirements |
|---|---|---|---|---|
| **ALLOW** | Yes, but only if the capability is implemented and advertised by the broker. | `status: success`, `policy_decision: ALLOW`, `execution_performed: true` | Not required. | None. |
| **DENY** | No. | `status: denied`, `policy_decision: DENY`, `execution_performed: false`, stable reason code. | N/A. | N/A. |
| **CONFIRM** | No until a valid single-use approval is presented. | `status: confirm_required`, `policy_decision: CONFIRM`, `execution_performed: false`. | Required from broker approval store; changed request invalidates approval. | `operator_confirmation`, possibly `vault_unlocked`, `verified_bundle`. |
| **DEFER** | No. | `status: deferred`, `policy_decision: DEFER`, `execution_performed: false`. | N/A. | Reported as unmet requirements; not treated as denial or success. |
| **ERROR** | No. | `status: denied`, `policy_decision: ERROR`, `execution_performed: false`. | N/A. | N/A. |
| **NOT_APPLICABLE** | Never allowed as a final decision. | Translated to DENY by the evaluator. | N/A. | N/A. |

## Broker Invariants

- `ALLOW` never bypasses capability advertisement or implementation checks.
- `DENY` is final; the broker cannot override it.
- `CONFIRM` never dispatches without a valid, single-use approval bound to the exact request.
- `DEFER` is not a soft-allow; it blocks dispatch and reports missing evidence.
- `ERROR` is fail-closed; it blocks dispatch.
- The broker never translates one state into another (e.g., it never turns `DEFER` into `ALLOW`, or `CONFIRM` into `DENY`).
