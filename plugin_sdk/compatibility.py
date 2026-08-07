"""Plugin compatibility negotiation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from plugin_sdk.errors import PluginCompatibilityError
from plugin_sdk.schema import SDK_VERSION

HIVE_VERSION: str = "1.0.0-dev"
BROKER_VERSION: str = "1.0"
POLICY_VERSION: str = "1.0"


@dataclass(frozen=True, slots=True)
class RuntimeVersions:
    hive: str
    broker: str
    sdk: str
    policy: str


def _parse_semver(version: str) -> tuple[int, int, int, str, str]:
    import re
    from plugin_sdk.schema import SEMVER_PATTERN
    m = SEMVER_PATTERN.match(version)
    if m:
        major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
        pre = m.group(4) or ""
        build = m.group(5) or ""
        return (major, minor, patch, pre, build)
    # Accept major.minor shorthand for SDK/broker version negotiation.
    loose = re.match(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$", version)
    if loose:
        return (int(loose.group(1)), int(loose.group(2)), 0, "", "")
    raise PluginCompatibilityError(f"not a semantic version: {version!r}")


def _compatible_major_minor(required: str, available: str) -> bool:
    req = _parse_semver(required)
    avail = _parse_semver(available)
    if req[0] != avail[0]:
        return False
    return (avail[1], avail[2]) >= (req[1], req[2])


def negotiate_compatibility(
    manifest: Dict[str, Any],
    broker_capabilities: set[str],
    runtime: RuntimeVersions | None = None,
) -> None:
    """Verify manifest compatibility with runtime. Raises PluginCompatibilityError on mismatch."""
    if runtime is None:
        runtime = RuntimeVersions(
            hive=HIVE_VERSION,
            broker=BROKER_VERSION,
            sdk=SDK_VERSION,
            policy=POLICY_VERSION,
        )

    compat = manifest["compatibility"]
    minimum_hive = compat["minimum_hive_version"]
    if not _compatible_major_minor(minimum_hive, runtime.hive):
        raise PluginCompatibilityError(
            f"incompatible Hive version: required {minimum_hive}, runtime {runtime.hive}"
        )

    required_broker = compat.get("required_broker_version")
    if required_broker is not None and not _compatible_major_minor(required_broker, runtime.broker):
        raise PluginCompatibilityError(
            f"incompatible broker version: required {required_broker}, runtime {runtime.broker}"
        )

    plugin_sdk_version = manifest["plugin"]["sdk_version"]
    if not _compatible_major_minor(plugin_sdk_version, runtime.sdk):
        raise PluginCompatibilityError(
            f"incompatible SDK version: plugin {plugin_sdk_version}, runtime {runtime.sdk}"
        )

    required_capabilities = set(compat.get("required_capabilities", []))
    missing = required_capabilities - broker_capabilities
    if missing:
        raise PluginCompatibilityError(
            f"required capabilities missing: {sorted(missing)}"
        )

    deps = manifest.get("dependencies", {})
    py_version = deps.get("python_version")
    if py_version is not None:
        import sys
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if not _compatible_major_minor(py_version, current):
            raise PluginCompatibilityError(
                f"incompatible Python version: required {py_version}, runtime {current}"
            )
