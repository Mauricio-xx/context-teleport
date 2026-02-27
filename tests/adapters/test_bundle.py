"""Tests for bundle import/export including security checks."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from ctx.adapters.bundle import (
    UnsafeBundleError,
    export_bundle,
    import_bundle,
)
from ctx.core.store import ContextStore
from ctx.utils.paths import STORE_DIR


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="bundle-test")
    return s


def _make_malicious_tar(tmp_path: Path, members: list[tuple[str, str | None]]) -> Path:
    """Create a tar.gz with specified members.

    members is a list of (name, content_or_None). If content is None, creates a
    symlink to /etc/passwd instead of a regular file.
    """
    tar_path = tmp_path / "evil.ctxbundle"
    with tarfile.open(tar_path, "w:gz") as tar:
        for name, content in members:
            if content is None:
                # Create a symlink member
                info = tarfile.TarInfo(name=name)
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                tar.addfile(info)
            else:
                data = content.encode()
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return tar_path


class TestBundleSecurity:
    def test_import_rejects_path_traversal(self, store, tmp_path):
        """Tar with ../../evil.txt member must be rejected."""
        tar_path = _make_malicious_tar(tmp_path, [
            (f"{STORE_DIR}/manifest.json", "{}"),
            ("../../evil.txt", "pwned"),
        ])
        with pytest.raises(UnsafeBundleError, match="path traversal"):
            import_bundle(store, tar_path)

    def test_import_rejects_absolute_path(self, store, tmp_path):
        """Tar with /etc/passwd member must be rejected."""
        tar_path = _make_malicious_tar(tmp_path, [
            (f"{STORE_DIR}/manifest.json", "{}"),
            ("/etc/passwd", "root:x:0:0"),
        ])
        with pytest.raises(UnsafeBundleError, match="absolute path"):
            import_bundle(store, tar_path)

    def test_import_rejects_symlink(self, store, tmp_path):
        """Tar with symlink pointing outside must be rejected."""
        tar_path = _make_malicious_tar(tmp_path, [
            (f"{STORE_DIR}/manifest.json", "{}"),
            (f"{STORE_DIR}/knowledge/evil-link.md", None),  # symlink
        ])
        with pytest.raises(UnsafeBundleError, match="link"):
            import_bundle(store, tar_path)


class TestBundleDryRun:
    def test_import_dry_run(self, store, tmp_path):
        """Dry run reports what would be imported without writing."""
        # Create a valid bundle first
        store.set_knowledge("test-key", "test content")
        bundle_path = tmp_path / "test.ctxbundle"
        export_bundle(store, bundle_path)

        # Create a fresh store to import into
        target = tmp_path / "target"
        target.mkdir()
        target_store = ContextStore(target)
        target_store.init(project_name="target")

        result = import_bundle(target_store, bundle_path, dry_run=True)
        assert result["dry_run"] is True
        assert result["imported"] == 0
        assert len(result["items"]) > 0
        # Verify nothing was actually written
        assert target_store.list_knowledge() == []

    def test_export_dry_run(self, store, tmp_path):
        """Dry run reports what would be bundled without creating archive."""
        store.set_knowledge("dry-test", "content")
        output_path = tmp_path / "out.ctxbundle"

        result = export_bundle(store, output_path, dry_run=True)
        assert result["dry_run"] is True
        assert len(result["items"]) > 0
        assert not output_path.exists()


class TestBundleRoundtrip:
    def test_export_import_roundtrip(self, store, tmp_path):
        """Export then import preserves knowledge."""
        store.set_knowledge("roundtrip", "hello world")
        bundle_path = tmp_path / "rt.ctxbundle"
        export_bundle(store, bundle_path)

        target = tmp_path / "target"
        target.mkdir()
        target_store = ContextStore(target)
        target_store.init(project_name="target")
        result = import_bundle(target_store, bundle_path)

        assert result["imported"] >= 1
        assert target_store.get_knowledge("roundtrip") is not None
