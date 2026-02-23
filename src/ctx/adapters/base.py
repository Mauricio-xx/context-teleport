"""AdapterProtocol: abstract interface for context adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


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

    def mcp_config_path(self) -> Path | None:
        """Return the path to this tool's MCP config file, or None if unsupported."""
        ...

    def register_mcp(self) -> dict:
        """Register ctx-mcp in the tool's MCP config."""
        ...

    def unregister_mcp(self) -> dict:
        """Remove ctx-mcp from the tool's MCP config."""
        ...
