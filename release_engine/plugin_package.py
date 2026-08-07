"""Plugin package format and signing.

Reuses Milestone 16 plugin manifest and Milestone 10 signing.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Dict

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from plugin_sdk.manifest import load_manifest as _load_plugin_manifest
from plugin_sdk.manifest import manifest_digest as _plugin_manifest_digest
from updates.errors import BundleError
from updates.signing import sign_metadata, verify_metadata
from updates.trust import TrustStore


def create_plugin_package(
    plugin_dir: Path,
    output_path: Path,
) -> Dict[str, Any]:
    """Create a deterministic plugin package from a plugin directory."""
    plugin_dir = plugin_dir.resolve()
    manifest_path = plugin_dir / "manifest.json"
    if not manifest_path.exists():
        raise BundleError("plugin package requires manifest.json")
    manifest_bytes = manifest_path.read_bytes()
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()

    files = sorted(p.relative_to(plugin_dir).as_posix() for p in plugin_dir.rglob("*") if p.is_file())

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in files:
            zf.write(plugin_dir / name, arcname=name)

    bundle_digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return {
        "plugin_id": _load_plugin_manifest(manifest_path)["plugin"]["id"],
        "version": _load_plugin_manifest(manifest_path)["plugin"]["version"],
        "manifest_digest": manifest_digest,
        "bundle_digest": bundle_digest,
        "files": files,
    }


def sign_plugin_package(
    metadata: Dict[str, Any],
    private_key: Ed25519PrivateKey,
    key_id: str,
) -> Dict[str, Any]:
    """Sign plugin package metadata."""
    return sign_metadata(metadata, private_key, key_id)


def verify_plugin_package(
    package_path: Path,
    work_dir: Path,
    trust_store: TrustStore,
) -> Dict[str, Any]:
    """Verify a plugin package signature and integrity."""
    import zipfile

    work_dir.mkdir(parents=True, exist_ok=True)
    stage_root = work_dir / "plugin"
    stage_root.mkdir(parents=True, exist_ok=True)
    # .hivepkg files are ZIP archives; extract safely.
    with zipfile.ZipFile(package_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename
            if name.startswith("/") or ".." in name.split("/") or ".." in name.split(chr(92)):
                raise BundleError(f"path traversal rejected: {name}")
            high = getattr(info, "external_attr", 0) >> 16
            if high:
                file_type = high & 0o170000
                if file_type == 0o120000:
                    raise BundleError(f"symlink rejected: {name}")
                if file_type and file_type != 0o100000:
                    raise BundleError(f"special file rejected: {name}")
        zf.extractall(stage_root)
    manifest_path = stage_root / "manifest.json"
    manifest = _load_plugin_manifest(manifest_path)

    metadata_path = stage_root / "metadata.json"
    if not metadata_path.exists():
        raise BundleError("plugin package missing metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    verify_metadata(metadata, trust_store)

    expected = metadata.get("manifest_digest", "")
    actual = _plugin_manifest_digest(manifest_path.read_text(encoding="utf-8"))
    if expected != actual:
        raise BundleError("plugin manifest digest mismatch")

    return {"verified": True, "plugin_id": manifest["plugin"]["id"], "metadata": metadata}
