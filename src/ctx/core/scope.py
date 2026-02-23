"""Scope metadata for knowledge and decision entries.

Scopes are stored in `.scope.json` sidecar files (one per directory).
Content files stay untouched -- scope is pure metadata.

Convention:
- public  = no entry in .scope.json (default)
- private = entry with value "private"
- ephemeral = entry with value "ephemeral"
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

SCOPE_FILENAME = ".scope.json"


class Scope(str, Enum):
    public = "public"
    private = "private"
    ephemeral = "ephemeral"


class ScopeMap:
    """Manages a .scope.json sidecar file for a single directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._path = directory / SCOPE_FILENAME

    def _read(self) -> dict[str, str]:
        if not self._path.is_file():
            return {}
        try:
            data = json.loads(self._path.read_text())
            if not isinstance(data, dict):
                return {}
            return data
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data: dict[str, str]) -> None:
        self._path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    def get(self, filename: str) -> Scope:
        """Return the scope for a filename. Absent entries are public."""
        data = self._read()
        raw = data.get(filename)
        if raw is None:
            return Scope.public
        try:
            return Scope(raw)
        except ValueError:
            return Scope.public

    def set(self, filename: str, scope: Scope) -> None:
        """Set scope for a filename. Setting public removes the entry."""
        data = self._read()
        if scope == Scope.public:
            data.pop(filename, None)
        else:
            data[filename] = scope.value
        self._write(data)

    def remove(self, filename: str) -> None:
        """Remove a filename from the sidecar (cleanup on file deletion)."""
        data = self._read()
        if filename in data:
            data.pop(filename)
            self._write(data)

    def list_by_scope(self, scope: Scope) -> list[str]:
        """Return filenames that have the given scope."""
        if scope == Scope.public:
            # Everything NOT in the sidecar is public -- caller must invert
            # This returns files explicitly in the sidecar, which are non-public.
            # For public listing, caller should subtract non_public_files().
            return []
        data = self._read()
        return [f for f, s in data.items() if s == scope.value]

    def non_public_files(self) -> set[str]:
        """Return the set of filenames with non-public scope."""
        data = self._read()
        return set(data.keys())

    @classmethod
    def ensure_exists(cls, directory: Path) -> None:
        """Create an empty .scope.json if it doesn't exist yet."""
        path = directory / SCOPE_FILENAME
        if not path.is_file():
            path.write_text("{}\n")
