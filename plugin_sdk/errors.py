"""Plugin SDK errors."""

from __future__ import annotations


class PluginError(Exception):
    """Base exception for Plugin SDK."""


class PluginManifestError(PluginError):
    """Manifest validation failed."""


class PluginIdentityError(PluginError):
    """Plugin identity verification failed."""


class PluginCompatibilityError(PluginError):
    """Plugin incompatible with Hive runtime."""


class PluginCapabilityError(PluginError):
    """Capability request denied or invalid."""


class PluginPolicyError(PluginError):
    """Policy Engine denied plugin request."""


class PluginConfigurationError(PluginError):
    """Plugin configuration invalid."""


class PluginLifecycleError(PluginError):
    """Lifecycle transition invalid."""


class PluginSignatureError(PluginError):
    """Signature metadata invalid."""


class PluginBundleError(PluginError):
    """Plugin bundle extraction failed."""


class PluginExecutionError(PluginError):
    """Plugin execution failed."""
