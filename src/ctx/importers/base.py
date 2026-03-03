"""Public protocol and data types for artifact importers.

Third-party packages implement ``ArtifactImporter`` and register classes via
the ``ctx.importers`` entry-point group.  The built-in EDA parsers also
conform to this protocol.

Security note for implementers
------------------------------
Importers **must** be read-only: they parse files and return structured data.
An importer must NEVER:

* modify or delete the source file,
* execute external commands or subprocesses,
* write files outside the context store.

Violating these constraints is a security risk and may result in the plugin
being rejected or blacklisted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

# Re-export ImportItem so third parties only need ``ctx.importers.base``.
from ctx.eda.parsers.base import ImportItem

__all__ = ["ArtifactImporter", "ImportItem"]


@runtime_checkable
class ArtifactImporter(Protocol):
    """Protocol for artifact importers (domain-agnostic).

    Identical shape to ``EdaImporter`` but intended as the public API for
    third-party plugin authors.  Built-in EDA parsers satisfy both protocols.
    """

    name: str

    def can_parse(self, path: Path) -> bool:
        """Return True if this importer can handle *path*."""
        ...

    def parse(self, path: Path) -> list[ImportItem]:
        """Parse the artifact at *path* and return knowledge items."""
        ...

    def describe(self) -> str:
        """Human-readable description of what this importer handles."""
        ...
