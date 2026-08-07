# Plugin Capabilities

Plugins declare requested capabilities. The authoritative capability registry is the Hive Broker + Policy Engine. The SDK does not invent capabilities.

## Grant Rules

A capability is granted only if it is:

1. Requested in the manifest
2. Advertised by the Broker
3. Authorized by the Policy Engine
4. Allowed for the plugin type
5. Allowed by the active profile

Unknown capabilities result in `DENY`.

## Read-Only Capabilities Allowed for `client`

- `service.status`, `service.list`, `service.health`, `service.graph`
- `broker.status`, `broker.capabilities`
- `policy.status`, `policy.profiles`, `policy.explain`
- `vault.status`
- `config.read.plugin`

## Always Denied

- All service start/stop/restart capabilities
- `update.apply`, `recovery.restore`
- `config.commit`, `config.write.global`
- `vault.secret.get`, `vault.secret.read`
- `policy.modify`, `broker.policy.modify`
- `shell`, `system.exec`, `system.subprocess`
- `network.listener`, `network.external`
- `plugin.self.grant`, `plugin.self.update`
- Any wildcard capability
