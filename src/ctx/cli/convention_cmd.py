"""Convention subcommands: list, get, add, rm, scope."""

from __future__ import annotations

import sys
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.core.scope import Scope
from ctx.utils.output import error, info, output, output_table, success

convention_app = typer.Typer(no_args_is_help=True)


def _parse_scope(value: str) -> Scope | None:
    if not value:
        return None
    try:
        return Scope(value.lower())
    except ValueError:
        return None


@convention_app.command("list")
def convention_list(
    scope: Optional[str] = typer.Option(None, "--scope", "-s", help="Filter by scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """List team conventions."""
    store = get_store()
    scope_filter = _parse_scope(scope) if scope else None
    entries = store.list_conventions(scope=scope_filter)
    if fmt == "json":
        items = []
        for e in entries:
            items.append({
                "key": e.key,
                "content": e.content,
                "scope": store.get_convention_scope(e.key).value,
            })
        output(items, fmt="json")
    else:
        if not entries:
            info("No conventions yet. Use `context-teleport convention add <key>` or `context-teleport import conventions <file>` to add some.")
            return
        rows = []
        for e in entries:
            rows.append({
                "key": e.key,
                "content": e.content[:60],
                "scope": store.get_convention_scope(e.key).value,
            })
        output_table(rows, columns=["key", "content", "scope"])


@convention_app.command("get")
def convention_get(
    key: str = typer.Argument(..., help="Convention key"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Print full convention content."""
    store = get_store()
    entry = store.get_convention(key)
    if entry is None:
        error(f"Convention '{key}' not found")
        raise typer.Exit(1)
    if fmt == "json":
        output({"key": entry.key, "content": entry.content}, fmt="json")
    else:
        output(entry.content, title=entry.key)


@convention_app.command("add")
def convention_add(
    key: str = typer.Argument(..., help="Convention key (e.g. 'git', 'environment')"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read content from file"),
    scope: Optional[str] = typer.Option(None, "--scope", "-s", help="Scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Create or update a convention from file, stdin, or empty template."""
    store = get_store()

    if file:
        from pathlib import Path

        text = Path(file).read_text()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        text = f"# {key}\n\nDescribe the convention here.\n"

    scope_val = _parse_scope(scope) if scope else None
    entry = store.set_convention(key, text, scope=scope_val)
    if fmt == "json":
        output({"key": entry.key, "status": "written"}, fmt="json")
    else:
        success(f"Convention '{entry.key}' written")


@convention_app.command("rm")
def convention_rm(
    key: str = typer.Argument(..., help="Convention key"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Remove a convention."""
    store = get_store()
    if store.rm_convention(key):
        if fmt == "json":
            output({"key": key, "status": "removed"}, fmt="json")
        else:
            success(f"Convention '{key}' removed")
    else:
        error(f"Convention '{key}' not found")
        raise typer.Exit(1)


@convention_app.command("scope")
def convention_scope(
    key: str = typer.Argument(..., help="Convention key"),
    scope: str = typer.Argument(..., help="New scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Change the scope of an existing convention."""
    store = get_store()
    scope_val = _parse_scope(scope)
    if scope_val is None:
        error(f"Invalid scope '{scope}'. Use public, private, or ephemeral.")
        raise typer.Exit(1)

    if store.set_convention_scope(key, scope_val):
        if fmt == "json":
            output({"key": key, "scope": scope_val.value, "status": "updated"}, fmt="json")
        else:
            success(f"Convention '{key}' scope set to {scope_val.value}")
    else:
        error(f"Convention '{key}' not found")
        raise typer.Exit(1)
