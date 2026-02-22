"""Knowledge subcommands: list, get, set, rm, search."""

from __future__ import annotations

import sys
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.core.search import search_files
from ctx.utils.output import error, info, output, output_table, success

knowledge_app = typer.Typer(no_args_is_help=True)


@knowledge_app.command("list")
def knowledge_list(fmt: Optional[str] = FORMAT_OPTION) -> None:
    """List knowledge entries."""
    store = get_store()
    entries = store.list_knowledge()
    if fmt == "json":
        output([{"key": e.key, "updated_at": str(e.updated_at)} for e in entries], fmt="json")
    else:
        if not entries:
            info("No knowledge entries yet. Use `ctx knowledge set <key>` to add one.")
            return
        output_table(
            [{"key": e.key, "updated": str(e.updated_at.date())} for e in entries],
            columns=["key", "updated"],
        )


@knowledge_app.command("get")
def knowledge_get(
    key: str = typer.Argument(..., help="Knowledge entry key"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Read a knowledge entry."""
    store = get_store()
    entry = store.get_knowledge(key)
    if entry is None:
        error(f"Knowledge entry '{key}' not found")
        raise typer.Exit(1)
    if fmt == "json":
        output({"key": entry.key, "content": entry.content}, fmt="json")
    else:
        output(entry.content, title=entry.key)


@knowledge_app.command("set")
def knowledge_set(
    key: str = typer.Argument(..., help="Knowledge entry key"),
    content: Optional[str] = typer.Argument(None, help="Content (reads stdin if omitted)"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read content from file"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Write or update a knowledge entry."""
    store = get_store()

    if file:
        from pathlib import Path

        text = Path(file).read_text()
    elif content:
        text = content
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        error("Provide content as argument, --file, or via stdin")
        raise typer.Exit(1)

    entry = store.set_knowledge(key, text)
    if fmt == "json":
        output({"key": entry.key, "status": "written"}, fmt="json")
    else:
        success(f"Knowledge '{entry.key}' written")


@knowledge_app.command("rm")
def knowledge_rm(
    key: str = typer.Argument(..., help="Knowledge entry key"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Remove a knowledge entry."""
    store = get_store()
    if store.rm_knowledge(key):
        if fmt == "json":
            output({"key": key, "status": "removed"}, fmt="json")
        else:
            success(f"Knowledge '{key}' removed")
    else:
        error(f"Knowledge entry '{key}' not found")
        raise typer.Exit(1)


@knowledge_app.command("search")
def knowledge_search(
    query: str = typer.Argument(..., help="Search query"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Full-text search across knowledge files."""
    store = get_store()
    results = search_files(store.knowledge_dir(), query)
    if fmt == "json":
        output(
            [
                {"key": r.key, "file": r.file, "line": r.line_number, "text": r.line, "score": r.score}
                for r in results
            ],
            fmt="json",
        )
    else:
        if not results:
            info(f"No results for '{query}'")
            return
        output_table(
            [
                {"key": r.key, "line": str(r.line_number), "match": r.line[:80]}
                for r in results[:20]
            ],
            columns=["key", "line", "match"],
        )
