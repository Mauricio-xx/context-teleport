"""Activity subcommands: list, check-in, check-out."""

from __future__ import annotations

from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.utils.output import error, info, output, output_table, success

activity_app = typer.Typer(no_args_is_help=True)


@activity_app.command("list")
def activity_list(
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """List team activity entries."""
    store = get_store()
    entries = store.list_activity()
    if fmt == "json":
        items = []
        for a in entries:
            items.append({
                "member": a.member,
                "agent": a.agent,
                "machine": a.machine,
                "task": a.task,
                "issue_ref": a.issue_ref,
                "status": a.status,
                "stale": store.is_stale(a),
            })
        output(items, fmt="json")
    else:
        if not entries:
            info("No active team members.")
            return
        rows = []
        for a in entries:
            stale = " (stale)" if store.is_stale(a) else ""
            rows.append({
                "member": a.member + stale,
                "task": a.task[:50],
                "issue": a.issue_ref,
                "agent": a.agent,
            })
        output_table(rows, columns=["member", "task", "issue", "agent"])


@activity_app.command("check-in")
def activity_check_in(
    task: str = typer.Argument(..., help="What you are working on"),
    issue: str = typer.Option("", "--issue", "-i", help="Issue reference (e.g. '#42')"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Check in to the team activity board."""
    store = get_store()
    entry = store.check_in(task=task, issue_ref=issue)
    if fmt == "json":
        output({"member": entry.member, "task": entry.task, "status": "checked_in"}, fmt="json")
    else:
        success(f"Checked in as '{entry.member}': {entry.task}")


@activity_app.command("check-out")
def activity_check_out(
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Check out from the team activity board."""
    store = get_store()
    removed = store.check_out()
    if removed:
        if fmt == "json":
            output({"status": "checked_out"}, fmt="json")
        else:
            success("Checked out from activity board")
    else:
        if fmt == "json":
            output({"status": "not_found"}, fmt="json")
        else:
            error("No active check-in found")
            raise typer.Exit(1)
