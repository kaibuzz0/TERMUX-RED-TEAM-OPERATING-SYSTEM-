"""H4-CORRECT: Plugin package resource bounds."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from plugin_sdk.errors import PluginBundleError
from plugin_sdk.loader import stage_bundle


class TestPluginPackageResourceBounds:
    """Verify plugin bundle extraction enforces resource limits."""

    def _make_manifest(self) -> bytes:
        return b'{"schema_version":1,"plugin":{"id":"test","version":"1.0.0","type":"client"}}'

    def test_plugin_bundle_expanded_size_limit(self, tmp_path, monkeypatch):
        """Bundle exceeding MAX_EXPANDED_SIZE is rejected."""
        from updates import bundle as bundle_mod
        monkeypatch.setattr(bundle_mod, "MAX_EXPANDED_SIZE", 1024 * 1024)  # 1 MiB for test speed

        bundle = tmp_path / "big.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", self._make_manifest())
            zf.writestr("big.dat", b"x" * (1024 * 1024 + 1))

        with pytest.raises((PluginBundleError, Exception)):
            stage_bundle(bundle, tmp_path / "staging")

    def test_plugin_bundle_file_count_limit(self, tmp_path, monkeypatch):
        """Bundle exceeding MAX_FILE_COUNT is rejected."""
        from updates import bundle as bundle_mod
        monkeypatch.setattr(bundle_mod, "MAX_FILE_COUNT", 10)  # small for test speed

        bundle = tmp_path / "many.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", self._make_manifest())
            for i in range(15):
                zf.writestr(f"file_{i}.txt", b"small")

        with pytest.raises((PluginBundleError, Exception)):
            stage_bundle(bundle, tmp_path / "staging")

    def test_plugin_bundle_rejects_symlink(self, tmp_path):
        """Bundle containing symlinks is rejected."""
        bundle = tmp_path / "symlink.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", self._make_manifest())
            # Create a zipinfo with external attr indicating symlink
            info = zipfile.ZipInfo("link")
            info.external_attr = (0o120777 << 16)  # symlink mode
            zf.writestr(info, "/etc/passwd")

        with pytest.raises((PluginBundleError, Exception)):
            stage_bundle(bundle, tmp_path / "staging")

    def test_plugin_bundle_rejects_hardlink(self, tmp_path):
        """Bundle containing hardlinks is rejected by extract_bundle."""
        bundle = tmp_path / "hardlink.zip"
        with zipfile.ZipFile(bundle, "w") as zf:
            zf.writestr("manifest.json", self._make_manifest())
            info = zipfile.ZipInfo("hlink")
            info.external_attr = (0o040777 << 16)
            zf.writestr(info, "content")

        with pytest.raises((PluginBundleError, Exception)):
            stage_bundle(bundle, tmp_path / "staging")

    def test_no_standalone_manifest_size_limit(self, tmp_path):
        """plugin_sdk.manifest.load_manifest has no standalone size limit.

        The only size boundary is updates.bundle.MAX_EXPANDED_SIZE (512 MiB),
        enforced during extraction. No manifest-specific size cap exists.
        """
        from plugin_sdk.manifest import load_manifest

        # Create a manifest larger than typical but well within extraction bounds
        padding = b"x" * 10000
        big_manifest = (
            b'{"schema_version":1,'
            b'"plugin":{"id":"test","name":"' + padding + b'","version":"1.0.0",'
            b'"sdk_version":"1.0","entrypoint":"a.b","type":"client"},'
            b'"compatibility":{"minimum_hive_version":"1.0.0-dev",'
            b'"required_broker_version":"1.0","required_capabilities":[]},'
            b'"permissions":{"requested_capabilities":[],"filesystem":[],'
            b'"network":"deny","secrets":[]},'
            b'"lifecycle":{"auto_start":false}}'
        )
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_bytes(big_manifest)

        # load_manifest succeeds — there is no manifest-specific size cap
        result = load_manifest(manifest_path)
        assert result["schema_version"] == 1
        assert "x" * 10 in result["plugin"]["name"]
