# Plugin SDK

HIVE OS plugins are capability-scoped clients. They may never bypass the Broker, Policy Engine, Configuration Engine, Service Supervisor, Vault, Update, or Recovery boundaries.

## Design Principles

- Plugins consume Hive capabilities through a stable Broker client.
- The Policy Engine authorizes every capability request.
- The Configuration Engine owns plugin configuration under `plugins.<plugin_id>`.
- Default plugin state is `DISABLED`.
- No arbitrary shell, network, secret, or mutation access.

## SDK Version

- Current SDK version: `1.0`
- Manifest schema version: `1`

## Supported Plugin Types

- `client` — uses Broker capabilities
- `collector` — read-only data collection
- `renderer` — transforms authorized data
- `validator` — validates bounded plugin-owned input

## Unsupported Plugin Types

`shell`, `daemon`, `kernel`, `network-listener`, `privileged`, `arbitrary-executor`.

## Quick Example

```python
from plugin_sdk import PluginIdentity
from plugin_sdk.broker_client import create_plugin_client

identity = PluginIdentity(...)
client = create_plugin_client(identity, ["service.status"])
result = client.request("service.status")
```
