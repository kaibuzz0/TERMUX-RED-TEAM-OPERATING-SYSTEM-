# Hive OS Operator Experience

**Version:** 1.1  
**Status:** Pass E — Operator UI / Hive Home / Notes / Speak / Safe Shell UX

---

## Hive Home

`hive` and `hive boot` launch the Hive OS operator landing page.

It is a lightweight stdlib-only interface rendered by `bin/hive_boot.py`,
backed by the `home.view_model` module.  Every telemetry field is read from
an authoritative subsystem:

- **Network profile/health** → `network.manager`
- **Supervisor/services** → `services.supervisor`
- **Policy/Broker/Vault/Trust** → existing broker/config APIs
- **Notes** → `hive_operator.notes`
- **Termux integration** → `installer.termux_repair`

No status is faked.  If a subsystem is degraded, the field is colored and
labelled accordingly.

---

## Layout

```text
                         Hive OS
                  Operator Environment

  Runtime      ONLINE
  Supervisor   HEALTHY
  Network      TOR
  Tor          HEALTHY
  Services     3/3 RUNNING
  Policy       ENFORCED
  Broker       AVAILABLE
  Vault        LOCKED
  Trust        VERIFIED
  Termux       INTEGRATED

  [1] Operations Center
  [2] Network
  [3] Services
  [4] Security / Audit
  [5] Vault
  [6] Plugins
  [7] Logs
  [8] Diagnostics
  [9] Termux Integration / Repair
  [N] Operator Notes
  [S] Speak
  [R] Refresh
  [0] Exit to Termux
```

---

## Menus

### [2] Network

Delegates to `hive net *`.

- Status
- DIRECT / ORBOT / TOR / HOLD
- Test
- New identity
- Run command through profile

HOLD is explained clearly:

> "HOLD disables Hive proxy execution and network-dependent services. It is
> NOT an Android device firewall."

### [3] Services

Delegates to `hive services *` / `hive start` / `hive stop`.

Displays name, state, health, PID, network, restarts.

### [4] Security / Audit

- `hive health`
- `hive doctor`
- `hive audit`
- `hive selftest`

Audit is read-only.  Selftest asks for confirmation and restores state.

### [7] Logs

- `hive logs`
- `hive rotate-logs`

### [8] Diagnostics

Surface supervisor summary, network health, Termux status.

### [9] Termux Integration / Repair

Preserved from 1.0.1 self-repair work.

---

## Operator Notes

Commands:

```text
hive notes show
hive notes edit
hive notes clear
hive notes info
```

Modern path: `~/.config/hive/operator-notes.txt`

Legacy `~/.hive_ops.txt` is read and migrated on first access, but never deleted.

Notes are **not a secret vault**. Do not store passwords or private keys here.

---

## `hive speak`

Read-only identity signal.  No network, no mutation, no shell execution.

---

## Optional Shell Integration

Managed, opt-in, removable shell aliases via:

```text
hive shell status
hive shell enable
hive shell disable
hive shell enable --shell zsh
hive shell disable --shell zsh
```

Requirements:

- Backs up original `.bashrc` / `.zshrc`
- Uses managed markers
- Preserves unrelated content
- Idempotent
- Removable
- Does not touch Hermes configuration outside Hive markers

Starship is **not required**.  `.zshrc` is supported if present.

---

## Autoboot UX

Opening Termux continues to launch Hive Home cleanly.  Exiting returns to a
normal usable Termux shell.  Non-TTY / redirected output degrades gracefully.

---

## Performance Model

Hive Home only reads fast local state.  Expensive probes (external Tor test,
audit, selftest) require explicit user selection.

---

## Failure Tolerance

A broken subsystem does not kill Hive Home.  Errors are captured, logged, and
displayed in the telemetry panel as `ERROR`.

---

## Color and TTY

Color is used only when:

- stdout is a TTY
- `NO_COLOR` is unset
- `TERM` is not `dumb`

Output remains readable without color.

---

*See `docs/NETWORK_MODEL.md`, `docs/SERVICE_SUPERVISOR.md`, `docs/DIAGNOSTICS_AND_LOGGING.md`, and `docs/ORIGINAL_RUNTIME_PARITY.md` for underlying models.*
