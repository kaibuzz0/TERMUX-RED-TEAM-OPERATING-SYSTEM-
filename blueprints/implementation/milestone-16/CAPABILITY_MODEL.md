# Capability Model

Plugins declare capabilities. Authority flows from Broker + Policy Engine.

## Grant Formula

granted = requested ∩ broker_advertised ∩ policy_allowed ∩ type_allowed ∩ profile_allowed

## Failures

- Missing broker capability → compatibility error
- Policy denial → policy error
- Type/profile denial → capability error


## Capability Grant Formula

```
granted_capabilities =
  requested_capabilities
  ∩ broker_advertised_capabilities
  ∩ policy_authorized_capabilities
  ∩ plugin_type_allowed_capabilities
  ∩ active_profile_allowed_capabilities
```

No wildcard expansion. No fallback to broader capability. No implicit capability from plugin type.
