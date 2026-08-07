# Plugin SDK Enforcement Audit

## Scope

This document proves that plugin requests cannot bypass the Broker, Policy Engine, Configuration Engine, Service Supervisor, Vault, Update, or Recovery boundaries in Milestone 16.

## Findings

### Plugin SDK never calls subsystem mutation internals directly

- `plugin_sdk/broker_client.py` only invokes `evaluate_plugin_capability` and a bounded `backend` callback.
- No imports from `services.cli`, `services.supervisor`, or service process APIs.
- No imports from `updates.cli`, `updates.recovery_cli`, or update/recovery internals.
- No imports from `installer` activation code.

### Plugin SDK never calls vault secret APIs directly

- `plugin_sdk/schema.py` lists `vault.secret.get` and `vault.secret.read` in `FORBIDDEN_CAPABILITIES`.
- `plugin_sdk/capabilities.py` lists vault secret access in `MUTATING_CAPABILITIES`.
- No vault `get` call appears in any `plugin_sdk/` production module.

### Plugin capabilities are evaluated by Policy Engine

- `plugin_sdk/policy.py` constructs plugin policy context with `actor_type=future_plugin`.
- `plugin_sdk/broker_client.py` calls `evaluate_plugin_capability` before invoking the backend.
- `ALLOW` is required before any broker-mediated operation proceeds.

### Broker remains enforcement point

- `PluginClient.request()` delegates to an externally supplied `backend`.
- The SDK does not dispatch adapters itself.
- The trusted runtime (Broker + Policy Engine) owns dispatch.

### Plugin actor identity is injected by trusted runtime

- `PluginIdentity` is constructed from the manifest digest and installation UUID.
- `PluginClient` receives the identity object; it cannot mint identities.
- `actor_id()` format: `plugin:<plugin_id>:<installation_id>`.

### Caller cannot spoof another plugin_id

- Manifest digest binds the declared plugin ID to canonical manifest bytes.
- `verify_identity_binding()` rejects mismatched plugin_id/version/digest.
- Registry lookup uses the identity's plugin_id, not a caller-supplied string.

### Caller cannot request ungranted capabilities

- `PluginClient.request()` checks `capability in self.granted` first.
- `validate_capability_set()` enforces requested ∩ broker ∩ policy ∩ type ∩ profile.

### Administrator profile does not bypass plugin restrictions

- No administrator-specific bypass in `plugin_sdk/capabilities.py`.
- `MUTATING_CAPABILITIES` are denied regardless of profile.
- Policy Engine is the single authority; profiles are bounded by policy rules.

### Development profile does not silently grant plugin mutation

- `auto_start` defaults to `false` and is treated as false in Milestone 16.
- Default lifecycle state is `DISABLED`.
- No implicit capability grant based on development mode.

### Emergency restrictions still apply

- Policy context carries `runtime_mode`.
- Emergency profiles reduce authority; they do not expand it.

## Conclusion

The Plugin SDK is a capability-scoped client. It cannot bypass the Broker or Policy Engine.
