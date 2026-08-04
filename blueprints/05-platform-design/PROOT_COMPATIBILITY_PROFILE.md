# PRoot Compatibility Profile

## Identity

Optional profile that uses PRoot for compatibility environments.

## Capabilities

- Run Linux distributions inside Termux.
- Provide isolated package environments.
- Useful for tools that require a full Linux userspace.

## Limitations

- PRoot is compatibility isolation, not security isolation.
- Same-UID bypass possible.
- Performance and storage overhead.
- Not a substitute for VM or kernel containment.

## Use cases

- Legacy tool compatibility.
- Distribution-specific build environments.
