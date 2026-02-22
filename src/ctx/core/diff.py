"""Compute diffs between store states."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileDiff:
    path: str
    status: str  # "added", "modified", "deleted"
    diff_text: str = ""


def diff_stores(old_root: Path, new_root: Path) -> list[FileDiff]:
    """Compute diffs between two store directories."""
    old_files = {str(f.relative_to(old_root)): f for f in old_root.rglob("*") if f.is_file()}
    new_files = {str(f.relative_to(new_root)): f for f in new_root.rglob("*") if f.is_file()}

    diffs = []

    # Deleted files
    for rel in sorted(set(old_files) - set(new_files)):
        diffs.append(FileDiff(path=rel, status="deleted"))

    # Added files
    for rel in sorted(set(new_files) - set(old_files)):
        diffs.append(FileDiff(path=rel, status="added"))

    # Modified files
    for rel in sorted(set(old_files) & set(new_files)):
        old_content = old_files[rel].read_text()
        new_content = new_files[rel].read_text()
        if old_content != new_content:
            diff_lines = difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            )
            diffs.append(
                FileDiff(
                    path=rel,
                    status="modified",
                    diff_text="".join(diff_lines),
                )
            )

    return diffs
