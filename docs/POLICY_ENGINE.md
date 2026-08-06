# Hive OS Policy Engine

The Policy Engine is the single authorization authority for Hive OS.

## Core principle

- The Policy Engine evaluates requests.
- It never executes actions.
- The Hive Broker remains the enforcement point.

## Decision states

- `ALLOW`
- `DENY`
- `CONFIRM`
- `DEFER`
- `NOT_APPLICABLE` (internal)
- `ERROR`

## Architecture

```text
CLI / Operations Center
        ↓
   Hive Broker
        ↓
Policy Engine
        ↓
Services · Vault · Updates · Recovery · Config Engine
```

## Components

- `requests.py` — strict request schema
- `decisions.py` — structured decisions
- `actors.py`, `capabilities.py`, `resources.py` — authoritative registries
- `conditions.py` — declarative conditions
- `requirements.py` — requirement evaluation
- `rules.py` — declarative rules and precedence
- `profiles.py` — built-in policy profiles
- `evaluator.py` — pure evaluation engine
- `engine.py` — facade and broker API
- `audit.py` — audit record generation
- `loader.py` — policy loading via config_engine
- `cli.py` — `hive policy *` commands
