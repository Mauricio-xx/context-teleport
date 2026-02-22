"""Decision subcommands: add, list, get."""

from __future__ import annotations

import os
import sys
import subprocess
import tempfile
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.utils.output import error, info, output, output_table, success

decision_app = typer.Typer(no_args_is_help=True)


@decision_app.command("list")
def decision_list(fmt: Optional[str] = FORMAT_OPTION) -> None:
    """List decision records."""
    store = get_store()
    decisions = store.list_decisions()
    if fmt == "json":
        output(
            [
                {"id": d.id, "title": d.title, "status": d.status.value, "date": str(d.date.date())}
                for d in decisions
            ],
            fmt="json",
        )
    else:
        if not decisions:
            info("No decisions recorded yet. Use `ctx decision add <title>` to create one.")
            return
        output_table(
            [
                {
                    "id": f"{d.id:04d}",
                    "title": d.title,
                    "status": d.status.value,
                    "date": str(d.date.date()),
                }
                for d in decisions
            ],
            columns=["id", "title", "status", "date"],
        )


@decision_app.command("get")
def decision_get(
    id_or_title: str = typer.Argument(..., help="Decision ID or title"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Read a decision record."""
    store = get_store()
    dec = store.get_decision(id_or_title)
    if dec is None:
        error(f"Decision '{id_or_title}' not found")
        raise typer.Exit(1)
    if fmt == "json":
        output(dec, fmt="json")
    else:
        output(dec.to_markdown())


@decision_app.command("add")
def decision_add(
    title: str = typer.Argument(..., help="Decision title"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read from file"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Create a new decision record (ADR)."""
    store = get_store()
    context_text = ""
    decision_text = ""
    consequences_text = ""

    if file:
        from pathlib import Path

        content = Path(file).read_text()
        # Parse sections from the file
        from ctx.core.schema import Decision

        parsed = Decision.from_markdown(content)
        context_text = parsed.context
        decision_text = parsed.decision
        consequences_text = parsed.consequences
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
        from ctx.core.schema import Decision

        parsed = Decision.from_markdown(content)
        context_text = parsed.context
        decision_text = parsed.decision
        consequences_text = parsed.consequences
    else:
        # Open $EDITOR
        editor = os.environ.get("EDITOR", "vi")
        template = f"""# {title}

## Context
Why this decision was needed.

## Decision
What was decided.

## Consequences
What follows.
"""
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as tmp:
            tmp.write(template)
            tmp_path = tmp.name

        try:
            subprocess.run([editor, tmp_path], check=True)
            content = open(tmp_path).read()
            from ctx.core.schema import Decision

            parsed = Decision.from_markdown(content)
            context_text = parsed.context
            decision_text = parsed.decision
            consequences_text = parsed.consequences
        except subprocess.CalledProcessError:
            error("Editor exited with error")
            raise typer.Exit(1)
        finally:
            os.unlink(tmp_path)

    dec = store.add_decision(
        title=title,
        context=context_text,
        decision_text=decision_text,
        consequences=consequences_text,
    )
    if fmt == "json":
        output(dec, fmt="json")
    else:
        success(f"Decision {dec.id:04d} created: {dec.title}")
