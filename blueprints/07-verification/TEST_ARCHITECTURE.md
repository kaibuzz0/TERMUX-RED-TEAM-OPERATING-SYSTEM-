# Test Architecture

## Three-level testing

### Level 1 — Static host tests
Run on Windows or desktop Linux:
- Inventory/schema validation.
- Python unit tests.
- Shell static analysis where tooling exists.
- Path-safety tests.
- Documentation consistency.
- Plugin unit tests with mocks.

### Level 2 — Linux compatibility tests
Run on desktop Linux containers or CI:
- Shell behavior.
- Filesystem transitions.
- Installer staging.
- Update rollback.
- Process supervision.
- Service manifests.

### Level 3 — Physical Android/Termux tests
Required for:
- `$PREFIX` behavior.
- Termux package availability.
- Shell interpreter behavior.
- Android storage permissions.
- Termux:API.
- Termux:Boot.
- Process persistence.
- Wake locks.
- Battery and thermal behavior.
- Symlink behavior.
- PRoot behavior.
- Native Python package installation.
- Actual install/update/repair.
- Session gate bypass analysis.
- Network listener behavior.

## Release gates

Every release gate identifies which test level supplies evidence.
