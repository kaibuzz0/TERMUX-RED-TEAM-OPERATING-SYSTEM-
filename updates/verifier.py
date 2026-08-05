"""Bundle verification orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

from updates.bundle import extract_bundle
from updates.errors import BundleError
from updates.manifest import load_manifest, verify_manifest
from updates.metadata import (
    check_compatibility,
    check_revocation,
    check_security_sequence,
    parse_metadata,
    verify_artifacts,
)
from updates.signing import verify_metadata
from updates.trust import TrustStore


class BundleVerifier:
    """Verify an offline update bundle before it is trusted."""

    def __init__(
        self,
        trust_store: TrustStore,
        platform: str,
        architecture: str,
        current_sequence: int = 0,
        current_release_id: str | None = None,
    ):
        self.trust_store = trust_store
        self.platform = platform
        self.architecture = architecture
        self.current_sequence = current_sequence
        self.current_release_id = current_release_id
        self.revoked_sequences: set[int] = set()

    def verify(self, bundle_path: Path, work_dir: Path, allow_emergency: bool = False) -> dict:
        """Extract, verify, and return verified metadata + manifest + extracted root."""
        work_dir.mkdir(parents=True, exist_ok=True)
        extract_bundle(bundle_path, work_dir)

        metadata_path = work_dir / "metadata.json"
        if not metadata_path.exists():
            raise BundleError("Bundle missing metadata.json")
        metadata = parse_metadata(metadata_path.read_text(encoding="utf-8"))

        # Trust verification
        try:
            verify_metadata(metadata, self.trust_store)
        except Exception:
            if not allow_emergency:
                raise

        check_compatibility(metadata, self.platform, self.architecture)
        check_security_sequence(metadata, self.current_sequence, self.current_release_id)
        check_revocation(metadata, self.revoked_sequences)
        verify_artifacts(metadata, work_dir)

        manifest = load_manifest(work_dir / "manifest.json")
        verify_manifest(manifest, work_dir)

        return {
            "verified": True,
            "metadata": metadata,
            "manifest": manifest,
            "bundle_root": work_dir,
            "trust_level": "offline_verified_bundle",
            "allow_emergency": allow_emergency,
        }

    def add_revoked_sequence(self, sequence: int) -> None:
        self.revoked_sequences.add(sequence)
