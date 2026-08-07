"""Basic software bill of materials."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class SbomComponent:
    name: str
    version: str
    hashes: Dict[str, str] | None = None
    type: str = "library"


def generate_sbom(
    release_version: str,
    sdk_version: str,
    components: List[SbomComponent] | None = None,
) -> Dict[str, Any]:
    """Generate a deterministic SBOM."""
    return {
        "schema_version": 1,
        "release_version": release_version,
        "plugin_sdk_version": sdk_version,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "components": [
            {
                "name": c.name,
                "version": c.version,
                "type": c.type,
                "hashes": c.hashes or {},
            }
            for c in (components or [])
        ],
    }
