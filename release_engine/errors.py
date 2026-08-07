"""Release engine errors."""

from __future__ import annotations


class ReleaseEngineError(Exception):
    """Base release engine error."""


class VersionError(ReleaseEngineError):
    pass


class BuildError(ReleaseEngineError):
    pass


class ManifestError(ReleaseEngineError):
    pass


class ReproducibilityError(ReleaseEngineError):
    pass


class ReleaseFormatError(ReleaseEngineError):
    pass


class ChannelError(ReleaseEngineError):
    pass


class RegistryError(ReleaseEngineError):
    pass


class DependencyError(ReleaseEngineError):
    pass
