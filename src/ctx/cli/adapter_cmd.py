"""Import/export subcommands: adapter operations and bundle I/O."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.utils.output import error, info, output, success

adapter_app = typer.Typer(no_args_is_help=True)
export_app = typer.Typer(no_args_is_help=True)


# -- Import commands (under `ctx import`) --


@adapter_app.command("claude-code")
def import_claude_code(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Extract from Claude Code internals into store."""
    store = get_store()
    from ctx.adapters.claude_code import ClaudeCodeAdapter

    adapter = ClaudeCodeAdapter(store)
    result = adapter.import_context(dry_run=dry_run)

    if fmt == "json":
        output(result, fmt="json")
    else:
        if dry_run:
            info("Dry run -- the following would be imported:")
            for item in result.get("items", []):
                info(f"  {item['type']}: {item['key']} ({item['source']})")
        else:
            imported = result.get("imported", 0)
            if imported:
                success(f"Imported {imported} items from Claude Code")
            else:
                info("Nothing to import from Claude Code")


@adapter_app.command("bundle")
def import_bundle(
    path: str = typer.Argument(..., help="Path to .ctxbundle archive"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import a portable context bundle archive."""
    store = get_store()
    from ctx.adapters.bundle import import_bundle as do_import

    result = do_import(store, Path(path))
    if fmt == "json":
        output(result, fmt="json")
    else:
        success(f"Imported bundle from {path}: {result.get('imported', 0)} items")


# -- Export commands (under `ctx export`) --


@export_app.command("claude-code")
def export_claude_code(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be exported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Inject store content into Claude Code locations."""
    store = get_store()
    from ctx.adapters.claude_code import ClaudeCodeAdapter

    adapter = ClaudeCodeAdapter(store)
    result = adapter.export_context(dry_run=dry_run)

    if fmt == "json":
        output(result, fmt="json")
    else:
        if dry_run:
            info("Dry run -- the following would be exported:")
            for item in result.get("items", []):
                info(f"  {item['target']}: {item['description']}")
        else:
            exported = result.get("exported", 0)
            if exported:
                success(f"Exported {exported} items to Claude Code")
            else:
                info("Nothing to export")


@export_app.command("bundle")
def export_bundle(
    path: str = typer.Argument(..., help="Output path for .ctxbundle archive"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Export store as a portable .ctxbundle archive."""
    store = get_store()
    from ctx.adapters.bundle import export_bundle as do_export

    result = do_export(store, Path(path))
    if fmt == "json":
        output(result, fmt="json")
    else:
        success(f"Bundle exported to {path}")
