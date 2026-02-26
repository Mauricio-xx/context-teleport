"""Bundle import/export: portable .ctxbundle archive format."""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from pathlib import Path

from ctx.core.migrations import SCHEMA_VERSION, check_version_compatible
from ctx.core.store import ContextStore
from ctx.utils.paths import STORE_DIR


class UnsafeBundleError(ValueError):
    """Raised when a bundle archive contains unsafe members (path traversal, symlinks)."""


def _safe_extractall(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract tar members after validating against path traversal and symlinks.

    Rejects:
    - Members with absolute paths
    - Members with '..' path components
    - Symlinks and hardlinks (bundles should only contain regular files/dirs)
    - Any member whose resolved path escapes the destination directory
    """
    dest = dest.resolve()
    for member in tar.getmembers():
        # Reject symlinks and hardlinks
        if member.issym() or member.islnk():
            raise UnsafeBundleError(
                f"Refusing to extract link in bundle: {member.name}"
            )

        # Reject absolute paths
        if member.name.startswith("/"):
            raise UnsafeBundleError(
                f"Refusing to extract absolute path in bundle: {member.name}"
            )

        # Reject '..' traversal
        if ".." in Path(member.name).parts:
            raise UnsafeBundleError(
                f"Refusing to extract path traversal in bundle: {member.name}"
            )

        # Final check: resolved path must stay within dest
        target = (dest / member.name).resolve()
        if not target.is_relative_to(dest):
            raise UnsafeBundleError(
                f"Refusing to extract member that escapes destination: {member.name}"
            )

    # All members validated, extract
    tar.extractall(dest, filter="data")


def export_bundle(store: ContextStore, output_path: Path, *, dry_run: bool = False) -> dict:
    """Export the context store as a .ctxbundle tar.gz archive."""
    store._require_init()

    if not output_path.suffix:
        output_path = output_path.with_suffix(".ctxbundle")

    manifest = store.read_manifest()

    if dry_run:
        # Collect what would be packaged
        items = []
        for f in sorted(store.store_dir.rglob("*")):
            if f.is_file():
                items.append({
                    "target": str(f.relative_to(store.root)),
                    "description": f"bundle {f.name}",
                })
        return {
            "path": str(output_path),
            "project": manifest.project.name,
            "dry_run": True,
            "items": items,
        }

    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(store.store_dir, arcname=STORE_DIR)

    return {
        "path": str(output_path),
        "project": manifest.project.name,
        "size_bytes": output_path.stat().st_size,
    }


def import_bundle(store: ContextStore, bundle_path: Path, *, dry_run: bool = False) -> dict:
    """Import a .ctxbundle archive into the store."""
    if not bundle_path.is_file():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    imported = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(bundle_path, "r:gz") as tar:
            _safe_extractall(tar, Path(tmpdir))

        extracted_store = Path(tmpdir) / STORE_DIR
        if not extracted_store.is_dir():
            raise ValueError("Invalid bundle: no .context-teleport directory found")

        # Check bundle version compatibility
        manifest_path = extracted_store / "manifest.json"
        if manifest_path.is_file():
            bundle_manifest = json.loads(manifest_path.read_text())
            bundle_version = bundle_manifest.get("schema_version", "0.1.0")
            if not check_version_compatible(bundle_version):
                raise ValueError(
                    f"Incompatible bundle version {bundle_version} "
                    f"(current: {SCHEMA_VERSION}). No migration path available."
                )

        # Dry run: report what would be imported without writing
        if dry_run:
            items = []
            knowledge_dir = extracted_store / "knowledge"
            if knowledge_dir.is_dir():
                for f in knowledge_dir.glob("*.md"):
                    items.append({"type": "knowledge", "key": f.stem, "source": f.name})
            decisions_dir = extracted_store / "knowledge" / "decisions"
            if decisions_dir.is_dir():
                for f in decisions_dir.glob("*.md"):
                    items.append({"type": "decision", "key": f.stem, "source": f.name})
            sessions_file = extracted_store / "history" / "sessions.ndjson"
            if sessions_file.is_file():
                items.append({"type": "sessions", "key": "sessions.ndjson", "source": "history"})
            return {"items": items, "imported": 0, "dry_run": True, "source": str(bundle_path)}

        # If store not initialized, copy wholesale
        if not store.initialized:
            shutil.copytree(extracted_store, store.store_dir)
            return {"imported": "all", "status": "initialized from bundle"}

        # Otherwise merge knowledge and decisions
        knowledge_dir = extracted_store / "knowledge"
        if knowledge_dir.is_dir():
            for f in knowledge_dir.glob("*.md"):
                target = store.knowledge_dir() / f.name
                target.write_text(f.read_text())
                imported += 1

        decisions_dir = extracted_store / "knowledge" / "decisions"
        if decisions_dir.is_dir():
            for f in decisions_dir.glob("*.md"):
                target = store.decisions_dir() / f.name
                if not target.exists():
                    target.write_text(f.read_text())
                    imported += 1

        # Merge sessions
        sessions_file = extracted_store / "history" / "sessions.ndjson"
        if sessions_file.is_file():
            existing_path = store.store_dir / "history" / "sessions.ndjson"
            existing_ids = set()
            if existing_path.is_file():
                for line in existing_path.read_text().strip().split("\n"):
                    if line.strip():
                        try:
                            obj = json.loads(line)
                            existing_ids.add(obj.get("id", ""))
                        except json.JSONDecodeError:
                            pass

            with open(existing_path, "a") as out:
                for line in sessions_file.read_text().strip().split("\n"):
                    if line.strip():
                        try:
                            obj = json.loads(line)
                            if obj.get("id", "") not in existing_ids:
                                out.write(line + "\n")
                                imported += 1
                        except json.JSONDecodeError:
                            pass

    return {"imported": imported, "source": str(bundle_path)}
