"""Interactive conflict resolution TUI for ctx pull --strategy interactive."""

from __future__ import annotations

import difflib
import os
import subprocess
import tempfile
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from ctx.core.conflicts import ConflictReport
from ctx.utils.output import console as default_console
from ctx.utils.output import is_piped


def interactive_resolve(
    report: ConflictReport,
    console: Console | None = None,
    prompt_fn: Callable[..., str] | None = None,
) -> list[tuple[str, str]]:
    """Walk the user through each conflict and collect resolutions.

    Args:
        report: ConflictReport with conflict entries (ours/theirs content captured).
        console: Rich console for output (injectable for tests).
        prompt_fn: Callable matching Prompt.ask signature (injectable for tests).

    Returns:
        List of (file_path, resolved_content) pairs. Skipped files are omitted.
    """
    console = console or default_console
    prompt_fn = prompt_fn or Prompt.ask

    if is_piped():
        console.print("[dim]Non-interactive mode detected, skipping interactive resolution[/dim]")
        return []

    unresolved = [c for c in report.conflicts if not c.resolved]
    if not unresolved:
        console.print("[dim]All conflicts already resolved[/dim]")
        return []

    resolutions: list[tuple[str, str]] = []
    choices: list[tuple[str, str]] = []  # (file_path, choice_label) for summary
    total = len(unresolved)

    for i, conflict in enumerate(unresolved, 1):
        console.print(Panel(
            f"[bold]{conflict.file_path}[/bold]",
            title=f"Conflict {i} of {total}",
        ))

        # Generate and display unified diff
        ours_lines = conflict.ours_content.splitlines(keepends=True)
        theirs_lines = conflict.theirs_content.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            ours_lines, theirs_lines,
            fromfile="ours", tofile="theirs",
        ))

        if diff_lines:
            diff_text = "".join(diff_lines)
            max_lines = 80
            display_lines = diff_text.splitlines()
            if len(display_lines) > max_lines:
                truncated = "\n".join(display_lines[:max_lines])
                remaining = len(display_lines) - max_lines
                truncated += f"\n... ({remaining} more lines)"
                diff_text = truncated
            console.print(Syntax(diff_text, "diff", theme="monokai"))
        else:
            console.print("[dim]No differences detected[/dim]")

        choice = prompt_fn(
            "[o]urs  [t]heirs  [e]dit  [s]kip",
            choices=["o", "t", "e", "s"],
            default="s",
        )

        if choice == "o":
            resolutions.append((conflict.file_path, conflict.ours_content))
            choices.append((conflict.file_path, "ours"))
        elif choice == "t":
            resolutions.append((conflict.file_path, conflict.theirs_content))
            choices.append((conflict.file_path, "theirs"))
        elif choice == "e":
            edited = _edit_content(conflict.ours_content)
            if edited is not None:
                resolutions.append((conflict.file_path, edited))
                choices.append((conflict.file_path, "edit"))
            else:
                choices.append((conflict.file_path, "skip (editor failed)"))
        else:
            choices.append((conflict.file_path, "skip"))

    # Summary table
    if choices:
        table = Table(title="Resolution Summary")
        table.add_column("File")
        table.add_column("Resolution")
        for file_path, label in choices:
            table.add_row(file_path, label)
        console.print(table)

    return resolutions


def _edit_content(initial_content: str) -> str | None:
    """Open $EDITOR with initial content, return edited result or None on failure."""
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as tmp:
        tmp.write(initial_content)
        tmp_path = tmp.name

    try:
        subprocess.run([editor, tmp_path], check=True)
        with open(tmp_path) as f:
            return f.read()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    finally:
        os.unlink(tmp_path)
