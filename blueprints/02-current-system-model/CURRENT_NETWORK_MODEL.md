# Current Network Model

**Static model.** Actual network behavior is **UNVERIFIED ON TERMUX**.

## Claimed network architecture

From `Hive Ops Final/bin/hive` and README:

```text
hive net orbot   → external Orbot app, SOCKS5 127.0.0.1:9050
hive net local   → bundled Tor, 127.0.0.1:9052
hive net off     → fail-closed (no proxy)
```

## Observed network-related files

| Path | Purpose | Listener risk |
|------|---------|---------------|
| `Hive Ops Final/bin/hive_net.core.sh` | Core networking functions (legacy) | UNVERIFIED |
| `Hive Ops Final/bin/hive_net.sh` | Network wrapper (legacy) | UNVERIFIED |
| `Hive Ops Final/bin/hive_proxy_run.sh` | Proxy runner (legacy) | UNVERIFIED |
| `Hive Ops Final/bin/hive_orbot_ui.sh` | Orbot UI helper (legacy) | UNVERIFIED |
| `Hive Ops DevAI/bin/hivedev-net` | DevAI network tool | UNVERIFIED |
| `Hive Ops DevAI/bin/hivedev-comms` | Communications tool | UNVERIFIED |
| `Hive Ops DevAI/bin/hivedev-gateway` | Gateway tool | UNVERIFIED |
| `brain-plug/therapist_code only.py` | Flask API server | Potential listener (UNVERIFIED) |
| Multiple `Hive Ops DevAI/bin/hivedev-*` scripts | Various network tools | Some reference `0.0.0.0`/listen/bind patterns statically |

## Static scan findings (high-level)

The security-risk-register static scan found `http.server`, `Flask`, `FastAPI`, `webhook`, `dashboard`, `0.0.0.0`, and `listen`/`bind` patterns in several files.

**Important:** These are string occurrences only. Whether any service actually listens on a non-loopback address by default is **UNVERIFIED ON TERMUX**.

## Default-address policy (target)

Current source does not enforce a "loopback-only by default" policy. The target architecture must add invariant INV-005: "No Hive-managed network service binds to a non-loopback address by default."

## External network dependencies

| Dependency | Purpose | Risk |
|------------|---------|------|
| GitHub (`github.com`) | clone, pull, update, repair | Compromised upstream / MITM / rollback |
| Termux package repositories | `pkg install` | Supply-chain substitution |
| PyPI | `pip install -r requirements.txt` | Supply-chain substitution |
| Orbot/Tor network | proxy routing | Traffic-analysis / misconfiguration |

## Network kill switch

`hive net off` is documented as fail-closed. On standard Termux, this is a policy script; true global firewall control is not available to unprivileged Termux.
