# Current Path Contract

**Milestone 4 — Pre-repair path analysis of canonical runtime spine**

## `Hive Ops Final/bin/hive`

| Type | Value | Line | Context | Category guess |
|------|-------|------|---------|----------------|
| root-hive | `/root/hive` | 32 | `OME = Path(os.environ.get('HIVE_HOME', '/root/hive')) HIVE_OS = Path('/root/hive-os') HIVE` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/hive-os` | 33 | `E_HOME', '/root/hive')) HIVE_OS = Path('/root/hive-os') HIVE_SWARM = Path('/root/hive-swarm')` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/hive-swarm` | 34 | `ath('/root/hive-os') HIVE_SWARM = Path('/root/hive-swarm') HIVE_CONFIG = Path.home() / '.config'` | STATE_ROOT / DATA_ROOT |
| root-hive | `/root/hive-swarm` | 72 | `OS / 'bin' / script,             Path(f'/root/hive-swarm/the-hive-tools/original hive os files/b` | STATE_ROOT / DATA_ROOT |

## `Hive Ops Final/bin/hive-dashboard`

| Type | Value | Line | Context | Category guess |
|------|-------|------|---------|----------------|
| root-hive | `/root/hive` | 16 | `Dict, List, Optional  HIVE_HOME = Path('/root/hive') HIVE_SWARM = Path('/root/hive-swarm')` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/hive-swarm` | 17 | `= Path('/root/hive') HIVE_SWARM = Path('/root/hive-swarm') HIVE_FINAL = Path('/root/Hive Ops Fin` | STATE_ROOT / DATA_ROOT |
| root-hive | `/root/Hive` | 18 | `('/root/hive-swarm') HIVE_FINAL = Path('/root/Hive Ops Final')  class HiveDashboard:     "` | LEGACY_INSTALL_ROOT / mixed |

## `Hive Ops Final/etc/env.sh`

| Type | Value | Line | Context | Category guess |
|------|-------|------|---------|----------------|
| root-hive | `/root/hive-os` | 7 | `$HOME/hive}" export HIVE_OS="${HIVE_OS:-/root/hive-os}" export HIVE_SWARM="${HIVE_SWARM:-/roo` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/hive-swarm` | 8 | `e-os}" export HIVE_SWARM="${HIVE_SWARM:-/root/hive-swarm}" export HIVE_FINAL="${HIVE_FINAL:-$HOM` | STATE_ROOT / DATA_ROOT |

## `Hive Ops Final/etc/services.json`

| Type | Value | Line | Context | Category guess |
|------|-------|------|---------|----------------|
| root-hive | `/root/Hive` | 5 | `e Hive daemon",       "start": "python3 /root/Hive Ops Final/bin/hive start",       "stop"` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/Hive` | 6 | `bin/hive start",       "stop": "python3 /root/Hive Ops Final/bin/hive stop",       "restar` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/Hive` | 7 | `n/hive stop",       "restart": "python3 /root/Hive Ops Final/bin/hive start",       "statu` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/Hive` | 8 | `n/hive start",       "status": "python3 /root/Hive Ops Final/bin/hive status",       "log"` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/hive` | 9 | `s Final/bin/hive status",       "log": "/root/hive/logs/supervisor.log",       "requires":` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/Hive` | 17 | `try passive'",       "status": "python3 /root/Hive Ops Final/lib/swarm_bridge.py status", ` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/hive` | 18 | `/swarm_bridge.py status",       "log": "/root/hive/logs/swarm.log",       "requires": [], ` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/hive` | 24 | `"System watchdog",       "start": "bash /root/hive/bin/hive_watchdog.sh",       "stop": "p` | LEGACY_INSTALL_ROOT / mixed |
| root-hive | `/root/hive` | 27 | `ning' \|\| echo 'stopped'",       "log": "/root/hive/logs/watchdog.log",       "requires": [` | LEGACY_INSTALL_ROOT / mixed |

