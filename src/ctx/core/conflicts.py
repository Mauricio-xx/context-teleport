"""Conflict detection and resolution for context merges."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Strategy(str, Enum):
    ours = "ours"
    theirs = "theirs"
    interactive = "interactive"
    agent = "agent"


@dataclass
class ConflictEntry:
    """A single file-level conflict."""
    file_path: str
    ours_content: str
    theirs_content: str
    base_content: str = ""
    resolved: bool = False
    resolution: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Summary dict with truncated previews (for CLI display)."""
        return {
            "file_path": self.file_path,
            "ours_preview": self.ours_content[:200],
            "theirs_preview": self.theirs_content[:200],
            "resolved": self.resolved,
        }

    def to_full_dict(self) -> dict[str, Any]:
        """Full serialization with complete content (for disk persistence)."""
        return {
            "file_path": self.file_path,
            "ours_content": self.ours_content,
            "theirs_content": self.theirs_content,
            "base_content": self.base_content,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConflictEntry:
        """Deserialize from a full dict."""
        return cls(
            file_path=data["file_path"],
            ours_content=data["ours_content"],
            theirs_content=data["theirs_content"],
            base_content=data.get("base_content", ""),
            resolved=data.get("resolved", False),
            resolution=data.get("resolution", ""),
        )


@dataclass
class ConflictReport:
    """Summary of all conflicts from a merge operation."""
    conflicts: list[ConflictEntry] = field(default_factory=list)
    auto_resolved: list[str] = field(default_factory=list)
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def has_conflicts(self) -> bool:
        return any(not c.resolved for c in self.conflicts)

    @property
    def unresolved_count(self) -> int:
        return sum(1 for c in self.conflicts if not c.resolved)

    def to_dict(self) -> dict[str, Any]:
        """Summary dict with previews (for CLI display)."""
        return {
            "has_conflicts": self.has_conflicts,
            "total": len(self.conflicts),
            "unresolved": self.unresolved_count,
            "auto_resolved": self.auto_resolved,
            "conflicts": [c.to_dict() for c in self.conflicts if not c.resolved],
        }

    def to_json(self) -> str:
        """Full JSON serialization for disk persistence."""
        return json.dumps({
            "conflict_id": self.conflict_id,
            "auto_resolved": self.auto_resolved,
            "conflicts": [c.to_full_dict() for c in self.conflicts],
        }, indent=2)

    @classmethod
    def from_json(cls, text: str) -> ConflictReport:
        """Deserialize from JSON string."""
        data = json.loads(text)
        return cls(
            conflict_id=data["conflict_id"],
            auto_resolved=data.get("auto_resolved", []),
            conflicts=[ConflictEntry.from_dict(c) for c in data.get("conflicts", [])],
        )


def resolve_conflicts(report: ConflictReport, strategy: Strategy) -> list[tuple[str, str]]:
    """Resolve all unresolved conflicts using the given strategy.

    Returns a list of (file_path, resolved_content) pairs.

    For 'interactive' and 'agent' strategies, this resolves nothing --
    those require external handling (CLI prompts or MCP tool calls).
    """
    resolutions: list[tuple[str, str]] = []

    for conflict in report.conflicts:
        if conflict.resolved:
            continue

        if strategy == Strategy.ours:
            conflict.resolution = conflict.ours_content
            conflict.resolved = True
            resolutions.append((conflict.file_path, conflict.ours_content))
        elif strategy == Strategy.theirs:
            conflict.resolution = conflict.theirs_content
            conflict.resolved = True
            resolutions.append((conflict.file_path, conflict.theirs_content))
        # interactive and agent are handled externally

    return resolutions


def resolve_single(report: ConflictReport, file_path: str, content: str) -> bool:
    """Resolve a single conflict by providing the final content.

    Returns True if the conflict was found and resolved.
    """
    for conflict in report.conflicts:
        if conflict.file_path == file_path and not conflict.resolved:
            conflict.resolution = content
            conflict.resolved = True
            return True
    return False
