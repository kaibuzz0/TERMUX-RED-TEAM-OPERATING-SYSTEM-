"""Release metadata schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ReleaseMetadata:
    """Canonical release metadata structure."""

    release_id: str
    version: str
    release_sequence: int
    schema_version: int
    build_id: str
    source_revision: str
    created_at: str
    minimum_supported_version: str
    platforms: List[str]
    architectures: List[str]
    manifest_digest: str
    artifact_digests: Dict[str, str]
    signing_key_id: str
    channel: str = "stable"
    dependencies: List[Dict[str, Any]] | None = None
    sbom: Dict[str, Any] | None = None
    provenance: Dict[str, Any] | None = None
