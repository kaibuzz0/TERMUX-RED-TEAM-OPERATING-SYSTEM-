"""Semantic release version handling."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

from release_engine.errors import VersionError


_VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[a-zA-Z0-9.]+))?$"
)


@dataclass(frozen=True)
class ReleaseVersion:
    major: int
    minor: int
    patch: int
    prerelease: str | None = None

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        return base

    @property
    def is_prerelease(self) -> bool:
        return self.prerelease is not None

    def compare(self, other: "ReleaseVersion") -> int:
        for a, b in ((self.major, other.major), (self.minor, other.minor), (self.patch, other.patch)):
            if a != b:
                return 1 if a > b else -1
        if self.prerelease is None and other.prerelease is not None:
            return 1
        if self.prerelease is not None and other.prerelease is None:
            return -1
        if self.prerelease is None and other.prerelease is None:
            return 0
        pa = self.prerelease.split(".")
        pb = other.prerelease.split(".")
        for x, y in zip(pa, pb):
            try:
                xi, yi = int(x), int(y)
                if xi != yi:
                    return 1 if xi > yi else -1
            except ValueError:
                if x != y:
                    return 1 if x > y else -1
        la, lb = len(pa), len(pb)
        if la != lb:
            return 1 if la > lb else -1
        return 0


def parse_release_version(value: str) -> ReleaseVersion:
    m = _VERSION_RE.match(value.strip())
    if not m:
        raise VersionError(f"invalid release version: {value}")
    return ReleaseVersion(
        major=int(m.group("major")),
        minor=int(m.group("minor")),
        patch=int(m.group("patch")),
        prerelease=m.group("prerelease"),
    )


def bump_major(version: ReleaseVersion) -> ReleaseVersion:
    return ReleaseVersion(major=version.major + 1, minor=0, patch=0)


def bump_minor(version: ReleaseVersion) -> ReleaseVersion:
    return ReleaseVersion(major=version.major, minor=version.minor + 1, patch=0)


def bump_patch(version: ReleaseVersion) -> ReleaseVersion:
    return ReleaseVersion(major=version.major, minor=version.minor, patch=version.patch + 1)
