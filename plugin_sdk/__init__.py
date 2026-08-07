"""HIVE OS Plugin SDK.

Plugins are consumers of Hive capabilities, never a backdoor around the
Broker, Policy Engine, Configuration Engine, or Service Supervisor.
"""

from plugin_sdk.errors import (
    PluginBundleError,
    PluginCapabilityError,
    PluginCompatibilityError,
    PluginConfigurationError,
    PluginError,
    PluginExecutionError,
    PluginIdentityError,
    PluginLifecycleError,
    PluginManifestError,
    PluginPolicyError,
    PluginSignatureError,
)
from plugin_sdk.identity import PluginIdentity, digest_capability_grant
from plugin_sdk.manifest import load_manifest, manifest_digest
from plugin_sdk.schema import SDK_VERSION, SCHEMA_VERSION

__all__ = [
    "PluginError",
    "PluginBundleError",
    "PluginCapabilityError",
    "PluginCompatibilityError",
    "PluginConfigurationError",
    "PluginExecutionError",
    "PluginIdentityError",
    "PluginLifecycleError",
    "PluginManifestError",
    "PluginPolicyError",
    "PluginSignatureError",
    "PluginIdentity",
    "digest_capability_grant",
    "load_manifest",
    "manifest_digest",
    "SDK_VERSION",
    "SCHEMA_VERSION",
]
