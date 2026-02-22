"""Three-way merge for knowledge (text) and JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MergeResult:
    content: str | dict
    has_conflicts: bool = False
    conflict_details: list[str] = field(default_factory=list)


def merge_json(base: dict, ours: dict, theirs: dict) -> MergeResult:
    """Field-level three-way merge for JSON objects.

    For each key:
    - If only one side changed, take that change
    - If both changed to the same value, take it
    - If both changed to different values, mark conflict
    """
    result = dict(base)
    conflicts = []

    all_keys = set(base) | set(ours) | set(theirs)

    for key in all_keys:
        base_val = base.get(key)
        our_val = ours.get(key)
        their_val = theirs.get(key)

        if our_val == their_val:
            # Both agree (or neither changed)
            if our_val is not None:
                result[key] = our_val
            elif key in result:
                del result[key]
        elif our_val == base_val:
            # Only theirs changed
            if their_val is not None:
                result[key] = their_val
            elif key in result:
                del result[key]
        elif their_val == base_val:
            # Only ours changed
            if our_val is not None:
                result[key] = our_val
            elif key in result:
                del result[key]
        else:
            # Both changed differently -- conflict
            result[key] = our_val  # default to ours
            conflicts.append(
                f"Conflict on '{key}': ours={json.dumps(our_val)}, theirs={json.dumps(their_val)}"
            )

    return MergeResult(
        content=result,
        has_conflicts=len(conflicts) > 0,
        conflict_details=conflicts,
    )


def merge_ndjson(ours: str, theirs: str) -> MergeResult:
    """Merge NDJSON files by taking the union of entries (by id field)."""
    seen_ids: set[str] = set()
    lines: list[str] = []

    for text in [ours, theirs]:
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                entry_id = obj.get("id", line)
                if entry_id not in seen_ids:
                    seen_ids.add(entry_id)
                    lines.append(line)
            except json.JSONDecodeError:
                lines.append(line)

    return MergeResult(content="\n".join(lines) + "\n" if lines else "", has_conflicts=False)
