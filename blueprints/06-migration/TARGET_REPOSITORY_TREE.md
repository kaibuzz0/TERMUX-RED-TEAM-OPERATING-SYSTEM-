# Target Repository Tree

**Status:** proposed. Not created in production yet.

## Proposed top-level layout

```text
TERMUX-RED-TEAM-OPERATING-SYSTEM-
├── README.md                      # Accurate, non-marketing documentation
├── install-termux.sh              # Transactional, verified installer
├── update.sh                      # Transactional, verified updater with rollback
├── repair.sh                      # Tiered repair (replaces emergency-repair.sh)
├── requirements.txt               # Pinned Python dependencies
├── pyproject.toml                 # Modern Python packaging + lock
├── uv.lock                        # Reproducible dependency lock
├── .github/
│   └── workflows/
│       └── ci.yml                 # Pinned Actions, tests, lint, security scan
├── core/                          # Canonical runtime
│   ├── bin/
│   │   ├── hive                   # Unified CLI
│   │   ├── hive-ui                # Terminal UI
│   │   └── hive-auth              # Login/authentication
│   ├── lib/
│   │   ├── shell_safe.sh          # Quoted-variable helpers
│   │   ├── swarm_bridge.py
│   │   └── policy_engine.py
│   ├── etc/
│   │   ├── env.sh
│   │   └── shell-integration.sh
│   ├── session-gate/
│   │   └── hive-session-gate.sh
│   ├── tools/
│   │   └── (curated security/ops tools)
│   └── services/
│       └── (service definitions)
├── policy/                        # Security policy
│   ├── seccomp/
│   ├── landlock/
│   ├── network/
│   └── capabilities/
├── integrations/
│   └── hermes/
│       ├── plugin/                # Hermes plugin (ctx.register_tool compatible)
│       ├── skills/
│       │   ├── hive-architect/
│       │   ├── hive-auditor/
│       │   ├── hive-builder/
│       │   └── hive-release-verifier/
│       └── profiles/
│           ├── architect.yaml
│           ├── auditor.yaml
│           ├── builder.yaml
│           └── reviewer.yaml
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── termux/
│   └── security/
├── docs/
│   ├── architecture/
│   ├── user-guide/
│   └── security/
├── scripts/
│   ├── build-sbom.sh
│   ├── sign-release.sh
│   └── verify-update.sh
├── archive/
│   └── devai-legacy/              # Hive Ops DevAI reference (read-only)
└── blueprints/                      # Architecture documents
```

## Terminology note

The directory `core/session-gate/` replaces any "secure boot" language. It implements a **Hive managed-session lock** or **Hive operator gate**, not Android device boot security.

## Directory ownership and rules

| Directory | Owner | Allowed dependencies | Forbidden dependencies | Test responsibility |
|-----------|-------|----------------------|------------------------|---------------------|
| `core/` | Hive core team | Termux packages, pinned PyPI, stdlib | Hermes core, unverified remote code | Unit + integration tests |
| `policy/` | Security team | stdlib, core lib | Network, secrets | Security tests |
| `integrations/hermes/` | Hermes integration team | Hermes plugin API, core interfaces | Direct Hermes core modification | Plugin tests |
| `tests/` | QA team | All production code | None | All test suites |
| `docs/` | Docs team | None | None | Docs tests |
| `scripts/` | Release team | core lib, gpg, git | Production runtime | Build/verify tests |
| `archive/` | Maintainers | None | Runtime code paths | Read-only reference |
| `blueprints/` | Architects | None | None | Review-only |

## Migration notes

- `Hive Ops Final/` content moves into `core/` and `archive/`.
- `Hive Ops DevAI/` content moves into `archive/devai-legacy/` or is selectively merged.
- `brain-plug/` moves into `integrations/brain-plug/`.
- `Hermes Plugins/` merges into `integrations/hermes/plugin/`.
