# Configuration Profiles

Profiles allow pre-defined configuration bundles with inheritance.

## Inheritance

A profile can inherit from another profile via `_parent` or `runtime.parent_profile`.

## Built-in profiles

See `docs/CONFIGURATION_ENGINE.md`.

## User profiles

Users may define custom profiles in `${config_root}/config.json`.

## Safety

- Circular inheritance is rejected.
- Profile names are sanitized.
- Unknown profiles raise `ConfigProfileError`.
