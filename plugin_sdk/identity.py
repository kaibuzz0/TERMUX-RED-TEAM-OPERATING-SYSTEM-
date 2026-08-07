"""Plugin identity and digest bindings."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from plugin_sdk.errors import PluginIdentityError


@dataclass(frozen=True, slots=True)
class PluginIdentity:
    """Immutable plugin identity used in broker actor and audit contexts."""

    plugin_id: str
    plugin_version: str
    manifest_digest: str
    installation_id: str
    publisher_id: str | None = None
    capability_grant_digest: str | None = None
    configuration_digest: str | None = None

    def actor_id(self) -> str:
        return f"plugin:{self.plugin_id}:{self.installation_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "manifest_digest": self.manifest_digest,
            "installation_id": self.installation_id,
            "publisher_id": self.publisher_id,
            "capability_grant_digest": self.capability_grant_digest,
            "configuration_digest": self.configuration_digest,
        }

    @classmethod
    def from_manifest(
        cls,
        manifest: Dict[str, Any],
        manifest_digest: str,
        installation_id: str | None = None,
        capability_grant_digest: str | None = None,
        configuration_digest: str | None = None,
    ) -> "PluginIdentity":
        plugin = manifest["plugin"]
        if installation_id is None:
            installation_id = str(uuid.uuid4())
        return cls(
            plugin_id=plugin["id"],
            plugin_version=plugin["version"],
            manifest_digest=manifest_digest,
            installation_id=installation_id,
            publisher_id=manifest.get("signature", {}).get("publisher_id"),
            capability_grant_digest=capability_grant_digest,
            configuration_digest=configuration_digest,
        )


def digest_capability_grant(
    plugin_id: str,
    granted_capabilities: list[str],
    profile_name: str,
    policy_decision: str,
) -> str:
    """Return deterministic digest of granted capability set."""
    payload = "|".join([
        plugin_id,
        ",".join(sorted(granted_capabilities)),
        profile_name,
        policy_decision,
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def digest_configuration(config: Dict[str, Any]) -> str:
    """Return deterministic digest of plugin configuration."""
    payload = json_canonical(config)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def json_canonical(value: Any) -> str:
    import json
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def verify_identity_binding(
    identity: PluginIdentity,
    manifest: Dict[str, Any],
    manifest_digest: str,
) -> None:
    """Verify that identity matches manifest and digest.

    Raises PluginIdentityError if binding is broken.
    """
    plugin = manifest["plugin"]
    if identity.plugin_id != plugin["id"]:
        raise PluginIdentityError("plugin_id mismatch")
    if identity.plugin_version != plugin["version"]:
        raise PluginIdentityError("plugin_version mismatch")
    if identity.manifest_digest != manifest_digest:
        raise PluginIdentityError("manifest_digest mismatch")
