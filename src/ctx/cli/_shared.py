"""Shared CLI utilities to avoid circular imports."""

from __future__ import annotations

import typer

from ctx.core.store import ContextStore
from ctx.utils.output import error
from ctx.utils.paths import find_project_root

FORMAT_OPTION = typer.Option(None, "--format", "-F", help="Output format: json or text")


def get_store() -> ContextStore:
    """Resolve the project root and return a ContextStore."""
    root = find_project_root()
    if root is None:
        error("Not inside a project directory (no .git or .context-teleport found)")
        raise typer.Exit(1)
    return ContextStore(root)
