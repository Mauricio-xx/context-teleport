"""Bundle import/export: portable .ctxbundle archive format."""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from pathlib import Path

from ctx.core.store import ContextStore
from ctx.utils.paths import STORE_DIR


def export_bundle(store: ContextStore, output_path: Path) -> dict:
    """Export the context store as a .ctxbundle tar.gz archive."""
    store._require_init()

    if not output_path.suffix:
        output_path = output_path.with_suffix(".ctxbundle")

    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(store.store_dir, arcname=STORE_DIR)

    manifest = store.read_manifest()
    return {
        "path": str(output_path),
        "project": manifest.project.name,
        "size_bytes": output_path.stat().st_size,
    }


def import_bundle(store: ContextStore, bundle_path: Path) -> dict:
    """Import a .ctxbundle archive into the store."""
    if not bundle_path.is_file():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    imported = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(tmpdir)

        extracted_store = Path(tmpdir) / STORE_DIR
        if not extracted_store.is_dir():
            raise ValueError("Invalid bundle: no .context-teleport directory found")

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
