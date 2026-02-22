"""Output formatting utilities: text vs JSON, rich panels."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


def is_piped() -> bool:
    return not sys.stdout.isatty()


def output(data: Any, fmt: str | None = None, title: str | None = None) -> None:
    """Output data in the requested format.

    If fmt is None, auto-detect: json when piped, text for TTY.
    """
    if fmt is None:
        fmt = "json" if is_piped() else "text"

    if fmt == "json":
        if isinstance(data, str):
            print(json.dumps({"value": data}))
        elif hasattr(data, "model_dump"):
            print(data.model_dump_json(indent=2))
        elif isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, default=str))
        else:
            print(json.dumps({"value": str(data)}, default=str))
    else:
        if isinstance(data, str):
            if title:
                console.print(Panel(data, title=title))
            else:
                console.print(data)
        elif hasattr(data, "model_dump"):
            console.print_json(data.model_dump_json(indent=2))
        elif isinstance(data, (dict, list)):
            console.print_json(json.dumps(data, default=str))
        else:
            console.print(str(data))


def output_table(rows: list[dict[str, str]], columns: list[str], fmt: str | None = None) -> None:
    if fmt is None:
        fmt = "json" if is_piped() else "text"

    if fmt == "json":
        print(json.dumps(rows, indent=2, default=str))
    else:
        table = Table()
        for col in columns:
            table.add_column(col.title())
        for row in rows:
            table.add_row(*[str(row.get(col, "")) for col in columns])
        console.print(table)


def error(msg: str) -> None:
    error_console.print(f"[red]Error:[/red] {msg}")


def success(msg: str) -> None:
    console.print(f"[green]{msg}[/green]")


def info(msg: str) -> None:
    console.print(f"[dim]{msg}[/dim]")
