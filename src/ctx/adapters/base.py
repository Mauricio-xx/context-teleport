"""AdapterProtocol: abstract interface for context adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ctx.core.store import ContextStore


@runtime_checkable
class AdapterProtocol(Protocol):
    """Interface that all adapters must implement."""

    name: str

    def detect(self) -> bool:
        """Check if this adapter's tool is installed and available."""
        ...

    def import_context(self, dry_run: bool = False) -> dict:
        """Extract context from the tool into the store."""
        ...

    def export_context(self, dry_run: bool = False) -> dict:
        """Inject store content into the tool's locations."""
        ...
