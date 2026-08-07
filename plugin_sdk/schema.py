"""Plugin manifest schema constants and field definitions."""

from __future__ import annotations

import re
from typing import AbstractSet, FrozenSet

SCHEMA_VERSION: int = 1
SDK_VERSION: str = "1.0"
SUPPORTED_PLUGIN_TYPES: FrozenSet[str] = frozenset({"client", "collector", "renderer", "validator"})
DEFAULT_PLUGIN_STATE: str = "DISABLED"
DEFAULT_NETWORK_POLICY: str = "deny"
DEFAULT_AUTO_START: bool = False

PLUGIN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9._-]*[a-z0-9]$")
PLUGIN_ID_MAX_LENGTH: int = 128
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9._-]+))?(?:\+([a-zA-Z0-9._-]+))?$")
ENTRYPOINT_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$")
CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9._-]*[a-z0-9]$")

FORBIDDEN_CAPABILITIES: FrozenSet[str] = frozenset({
    "shell",
    "system.exec",
    "system.subprocess",
    "policy.modify",
    "policy.bypass",
    "vault.secret.get",
    "vault.secret.read",
    "update.apply",
    "recovery.restore",
    "config.commit",
    "config.write.global",
    "service.start",
    "service.stop",
    "service.restart",
    "broker.policy.modify",
    "network.listener",
    "network.external",
    "plugin.self.grant",
    "plugin.self.update",
    "*",
})

WILDCARD_PATTERN = re.compile(r"(\*|<.*>|%.*)")

REQUIRED_MANIFEST_SECTIONS: FrozenSet[str] = frozenset({"schema_version", "plugin", "compatibility", "permissions", "lifecycle"})

MAX_BUNDLE_SIZE: int = 10 * 1024 * 1024
MAX_BUNDLE_FILES: int = 1000
MAX_BUNDLE_PATH_LENGTH: int = 256
MAX_RESULT_SIZE: int = 256 * 1024
MAX_STDOUT_SIZE: int = 64 * 1024
MAX_STDERR_SIZE: int = 64 * 1024
PLUGIN_REQUEST_TIMEOUT: float = 30.0
