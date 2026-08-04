# Security Risk Register

**Important qualification:** This register is based on **static analysis from a Windows host**. Every risk related to runtime behavior, Termux execution, Android APIs, or network binding is labeled **UNVERIFIED ON TERMUX** unless otherwise stated. A physical Android test is required to confirm exploitability or actual behavior.

— Initial Static Findings

| File | Risk Category | Occurrences | Sample(s) |
|------|---------------|-------------|-----------|
| `README.md` | curl_pipe_bash | 2 | `curl -fsSL https://raw.githubusercontent.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-`<br>`curl -fsSL https://raw.githubusercontent.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-` |
| `install-termux.sh` | curl_pipe_bash | 1 | `curl -fsSL https://raw.githubusercontent.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-` |
| `install.sh` | curl_pipe_bash | 1 | `curl -fsSL https://raw.githubusercontent.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-` |
| `Hive Ops DevAI/bin/hivedev-log` | eval | 1 | `eval` |
| `Hive Ops DevAI/bin/hivedev-swarm-manager` | eval | 1 | `eval` |
| `Hive Ops DevAI/hive-swarm.py` | eval | 1 | `eval` |
| `Hive Ops DevAI/hive_agents.py` | eval | 1 | `eval` |
| `Hive Ops Final/shell/.zshrc` | eval | 1 | `eval` |
| `Hive Ops Final/swarm-core/agents/architect_agent.py` | eval | 1 | `eval` |
| `Hive Ops Final/swarm-core/hive-swarm.py` | eval | 1 | `eval` |
| `update.sh` | git_stash | 1 | `git stash` |
| `Hive Ops DevAI/bin/hive-hermes` | http_server | 10 | `dashboard`<br>`Dashboard`<br>`dashboard` |
| `Hive Ops DevAI/bin/hive-os` | http_server | 3 | `dashboard`<br>`dashboard`<br>`dashboard` |
| `Hive Ops DevAI/bin/hive-ui` | http_server | 29 | `dashboard`<br>`Dashboard`<br>`Dashboard` |
| `Hive Ops DevAI/bin/hivedev-pet` | http_server | 1 | `dashboard` |
| `Hive Ops DevAI/swarm_pet.py` | http_server | 1 | `dashboard` |
| `Hive Ops Final/README.md` | http_server | 6 | `dashboard`<br>`dashboard`<br>`dashboard` |
| `Hive Ops Final/bin/hive` | http_server | 9 | `dashboard`<br>`dashboard`<br>`dashboard` |
| `Hive Ops Final/bin/hive-dashboard` | http_server | 10 | `Dashboard`<br>`dashboard`<br>`Dashboard` |
| `Hive Ops Final/bin/hive-secure-login` | http_server | 2 | `dashboard`<br>`dashboard` |
| `Hive Ops Final/etc/bash-integration.sh` | http_server | 2 | `dashboard`<br>`dashboard` |
| `Hive Ops Final/etc/env.sh` | http_server | 1 | `dashboard` |
| `Hive Ops Final/original hive os complete/etc/services/_TEMPLATE.svc` | http_server | 1 | `http.server` |
| `Hive Ops Final/original hive os complete/etc/services/mini-ai.svc` | http_server | 1 | `http.server` |
| `Hive Ops Final/swarm-core/registry/HSL_DEFINITION.md` | http_server | 1 | `dashboard` |
| `Hive Ops Final/swarm-core/swarm_pet.py` | http_server | 1 | `dashboard` |
| `README.md` | http_server | 4 | `dashboard`<br>`dashboard`<br>`dashboard` |
| `blueprints/00-baseline/head_inspection_dump.md` | http_server | 13 | `dashboard`<br>`dashboard`<br>`dashboard` |
| `blueprints/00-baseline/raw_inventory.json` | http_server | 1 | `dashboard` |
| `blueprints/01-repository-forensics/COMPLETE_FILE_INVENTORY.md` | http_server | 1 | `dashboard` |
| `brain-plug/therapist_code only.py` | http_server | 2 | `Flask(`<br>`Flask(` |
| `install-termux.sh` | http_server | 2 | `dashboard`<br>`dashboard` |
| `install.sh` | http_server | 1 | `dashboard` |
| `Hive Ops DevAI/bin/hivedev-node` | public_listen | 1 | `0.0.0.0` |
| `README.md` | rm_rf | 2 | `rm -rf`<br>`rm -rf` |
| `emergency-repair.sh` | rm_rf | 3 | `rm -rf`<br>`rm -rf`<br>`rm -rf` |
| `install-termux.sh` | rm_rf | 1 | `rm -rf` |
| `Hermes Plugins/install.sh` | unquoted_variable | 16 | `$HERMES_HOME`<br>`$HERMES_HOME`<br>`$HIVE_SOURCE` |
| `Hive Ops DevAI/bin/hive-boot` | unquoted_variable | 1 | `$HOME` |
| `Hive Ops DevAI/bin/hive-ui` | unquoted_variable | 1 | `$HOME` |
| `Hive Ops Final/.termux/boot/00-hive-ops.sh` | unquoted_variable | 13 | `$HOME`<br>`$ENV_FILE`<br>`$ENV_FILE` |
| `Hive Ops Final/.termux/boot/00-hive-secure.sh` | unquoted_variable | 15 | `$HOME`<br>`$HIVE_FINAL`<br>`$SECURE_LOGIN` |
| `Hive Ops Final/bin/hive-secure-login` | unquoted_variable | 57 | `$HOME`<br>`$HIVE_DIR`<br>`$HOME` |
| `Hive Ops Final/etc/bash-integration.sh` | unquoted_variable | 31 | `$HOME`<br>`$HIVE_FINAL`<br>`$HIVE_FINAL` |
| `Hive Ops Final/etc/env.sh` | unquoted_variable | 19 | `$HOME`<br>`$HOME`<br>`$HIVE_HOME` |
| `Hive Ops Final/original hive os complete/.config/hive/env.sh` | unquoted_variable | 10 | `$HOME`<br>`$HIVE_HOME`<br>`$HIVE_HOME` |
| `Hive Ops Final/original hive os complete/.termux/boot/00-hive.sh` | unquoted_variable | 7 | `$HOME`<br>`$ENV_FILE`<br>`$ENV_FILE` |
| `Hive Ops Final/original hive os complete/bin/hive` | unquoted_variable | 43 | `$code`<br>`$HOME`<br>`$HIVE_BIN` |
| `Hive Ops Final/original hive os complete/bin/hive_logrotate.sh` | unquoted_variable | 16 | `$HOME`<br>`$LOG_DIR`<br>`$f` |
| `Hive Ops Final/original hive os complete/bin/hive_net.core.sh` | unquoted_variable | 50 | `$line`<br>`$cmd`<br>`$code` |
| `Hive Ops Final/original hive os complete/bin/hive_net.sh` | unquoted_variable | 6 | `$HOME`<br>`$HIVE_BIN`<br>`$sub` |
| `Hive Ops Final/original hive os complete/bin/hive_proxy_run.sh` | unquoted_variable | 13 | `$code`<br>`$HOME`<br>`$HIVE_STATE` |
| `Hive Ops Final/original hive os complete/bin/hive_ps.sh` | unquoted_variable | 5 | `$HOME`<br>`$HOME`<br>`$pids` |
| `Hive Ops Final/original hive os complete/bin/hive_restart.sh` | unquoted_variable | 2 | `$HOME`<br>`$HOME` |
| `Hive Ops Final/original hive os complete/bin/hive_rotator.sh` | unquoted_variable | 6 | `$HOME`<br>`$HOME`<br>`$HIVE_LOGS` |
| `Hive Ops Final/original hive os complete/bin/hive_services.sh` | unquoted_variable | 78 | `$line`<br>`$cmd`<br>`$code` |
| `Hive Ops Final/original hive os complete/bin/hive_supervisor.sh` | unquoted_variable | 6 | `$HOME`<br>`$HOME`<br>`$HIVE_LOG` |
| `Hive Ops Final/original hive os complete/bin/hive_watchdog.sh` | unquoted_variable | 28 | `$code`<br>`$HOME`<br>`$HIVE_STATE` |
| `Hive Ops Final/original hive os complete/bin/step5.1_fix_health.sh` | unquoted_variable | 40 | `$f`<br>`$f`<br>`$f` |
| `Hive Ops Final/original hive os complete/etc/mini-ai.env` | unquoted_variable | 2 | `$HOME`<br>`$HOME` |
| `Hive Ops Final/original hive os complete/etc/services/_TEMPLATE.service` | unquoted_variable | 1 | `$HOME` |
| `Hive Ops Final/original hive os complete/etc/services/_TEMPLATE.svc` | unquoted_variable | 2 | `$HIVE_LOG`<br>`$HIVE_LOG` |
| `Hive Ops Final/original hive os complete/hive_bootstrap.sh` | unquoted_variable | 87 | `$p`<br>`$p`<br>`$LINENO` |
| `Hive Ops Final/shell/.bashrc` | unquoted_variable | 32 | `$HOME`<br>`$HOME`<br>`$HOME` |
| `Hive Ops Final/shell/.zshrc` | unquoted_variable | 4 | `$HOME`<br>`$HOME`<br>`$HOME` |
| `blueprints/00-baseline/head_inspection_dump.md` | unquoted_variable | 96 | `$HOME`<br>`$HIVE_DIR`<br>`$HOME` |
| `emergency-repair.sh` | unquoted_variable | 62 | `$HOME`<br>`$HOME`<br>`$REPLY` |
| `install-termux.sh` | unquoted_variable | 55 | `$HOME`<br>`$HOME`<br>`$LOG_FILE` |
| `install.sh` | unquoted_variable | 77 | `$HOME`<br>`$HOME`<br>`$LOG_FILE` |
| `update.sh` | unquoted_variable | 42 | `$HOME`<br>`$HOME`<br>`$INSTALL_DIR` |
