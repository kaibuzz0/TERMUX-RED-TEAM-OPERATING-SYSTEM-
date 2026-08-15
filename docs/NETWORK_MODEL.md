# Hive OS Network Model

**Version:** 1.1  
**Status:** Pass B — Modern Network Foundation

This document defines the authoritative Hive OS network profiles, health model, and security boundaries.

---

## Profiles

Hive OS supports four network profiles.

### DIRECT

Normal, unproxied application networking.

- Hive does not configure any proxy environment.
- `ALL_PROXY`, `HTTP_PROXY`, `HTTPS_PROXY`, and related variables are cleared.
- Services that require *any* network may run.
- Services that require a proxied profile may **not** run.

### ORBOT

Hive applications use an externally managed Orbot SOCKS endpoint.

- Configured default: `127.0.0.1:9050`
- Hive reports SOCKS reachability only; it does not manage the Orbot app.
- Orbot UI may be launched with `hive net orbot-ui` if the Android activity manager is available.

### TOR

Hive manages a local Tor daemon and uses its SOCKS endpoint.

- Configured default: `127.0.0.1:9052`
- ControlPort default: `127.0.0.1:9051`
- Cookie authentication required.
- Loopback-only listeners.
- Hive starts and stops the Tor process.

### HOLD

Hive treats network-dependent Hive operations and services as unavailable.

- Proxy execution is disabled.
- Network-dependent services are stopped by the supervisor (Pass C).
- **HOLD is not a device firewall.** It does not disable Android networking, Wi-Fi, mobile data, or non-Hive applications.

---

## Compatibility Aliases

For compatibility with the original Hive OS command surface:

- `hive net local` is an alias for `hive net tor`.
- `hive net off` is an alias for `hive net hold`.

Both emit a compatibility notice explaining the modern semantics.

---

## Health Layers

Hive distinguishes these health levels so that a responding TCP port is never treated as "Tor healthy":

1. **SOCKS_LISTENER** — TCP port responds.
2. **TOR_PROCESS** — A local tor process is tracked.
3. **CONTROL_PORT** — ControlPort responds.
4. **BOOTSTRAP** — Tor reports 100% bootstrap.
5. **PROXY_REQUEST** — An HTTP request through SOCKS succeeds.
6. **TOR_CONFIRMATION** — Optional explicit Tor exit confirmation.

A profile is **HEALTHY** only when every required layer for that profile passes.

---

## Security Boundaries

- Hive network profiles control Hive-aware/Termux application routing.
- They do **not** automatically provide device-wide Android anonymity.
- They do **not** act as a kernel firewall.
- ControlPort and SOCKS bind loopback only.
- Cookie-based authentication material is never logged or committed.
- Service logs must not contain proxy credentials or session secrets.

---

## Exit Codes

- `0` — Healthy / success
- `1` — General failure
- `2` — Unavailable / SOCKS down
- `3` — Degraded
- `4` — Tor confirmation failed
- `5` — Proxy execution refused / no command

---

## Commands

| Command | Purpose |
|---------|---------|
| `hive net status` | Show current profile and health |
| `hive net status --json` | Machine-readable status |
| `hive net direct` | Switch to direct networking |
| `hive net orbot` | Switch to Orbot SOCKS |
| `hive net tor` | Start and use Hive-managed Tor |
| `hive net hold` | Disable Hive proxy execution |
| `hive net local` | Compatibility alias for `tor` |
| `hive net off` | Compatibility alias for `hold` |
| `hive net test` | Run layered network test |
| `hive net newnym` | Renew Tor identity (TOR only) |
| `hive net orbot-ui` | Launch Orbot UI if available |
| `hive net run -- CMD ARGS` | Run command through current profile |

---

*See `docs/ORIGINAL_RUNTIME_PARITY.md` for the full OG-to-modern mapping.*
