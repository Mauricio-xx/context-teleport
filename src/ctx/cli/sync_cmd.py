"""Sync subcommands: push, pull, diff, log. Also registers top-level shortcuts."""

from __future__ import annotations

from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.utils.output import error, info, output, success

sync_app = typer.Typer(no_args_is_help=True)


@sync_app.command("push")
def sync_push(
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Commit message"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Stage context changes, commit, and push."""
    store = get_store()
    from ctx.sync.git_sync import GitSync

    gs = GitSync(store.root)
    result = gs.push(message=message)
    if fmt == "json":
        output(result, fmt="json")
    else:
        status = result.get("status")
        msg = result.get("commit_message", "")
        if status == "pushed":
            success(f"Context pushed: {msg}")
        elif status == "committed":
            success(f"Context committed (no remote): {msg}")
            if result.get("push_error"):
                info(f"Push skipped: {result['push_error']}")
        elif status == "nothing_to_push":
            info("No context changes to push")
        else:
            error(result.get("error", "Push failed"))


@sync_app.command("pull")
def sync_pull(fmt: Optional[str] = FORMAT_OPTION) -> None:
    """Pull remote context and merge."""
    store = get_store()
    from ctx.sync.git_sync import GitSync

    gs = GitSync(store.root)
    result = gs.pull()
    if fmt == "json":
        output(result, fmt="json")
    else:
        if result.get("status") == "pulled":
            success("Context pulled and merged")
        elif result.get("status") == "up_to_date":
            info("Already up to date")
        else:
            error(result.get("error", "Pull failed"))


@sync_app.command("diff")
def sync_diff(
    remote: bool = typer.Option(False, "--remote", help="Compare with remote"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Show context changes."""
    store = get_store()
    from ctx.sync.git_sync import GitSync

    gs = GitSync(store.root)
    result = gs.diff(remote=remote)
    if fmt == "json":
        output(result, fmt="json")
    else:
        diff_text = result.get("diff", "")
        if diff_text:
            from ctx.utils.output import console

            console.print(diff_text)
        else:
            info("No changes")


@sync_app.command("log")
def sync_log(
    oneline: bool = typer.Option(False, "--oneline", help="One-line format"),
    count: int = typer.Option(10, "-n", help="Number of entries"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Show context change history."""
    store = get_store()
    from ctx.sync.git_sync import GitSync

    gs = GitSync(store.root)
    result = gs.log(oneline=oneline, count=count)
    if fmt == "json":
        output(result, fmt="json")
    else:
        log_text = result.get("log", "")
        if log_text:
            from ctx.utils.output import console

            console.print(log_text)
        else:
            info("No context history")


def register_sync_shortcuts(app: typer.Typer) -> None:
    """Register push/pull/diff/log as top-level commands."""

    @app.command("push")
    def push_shortcut(
        message: Optional[str] = typer.Option(None, "--message", "-m"),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Stage context changes, commit, and push."""
        sync_push(message=message, fmt=fmt)

    @app.command("pull")
    def pull_shortcut(fmt: Optional[str] = FORMAT_OPTION) -> None:
        """Pull remote context and merge."""
        sync_pull(fmt=fmt)

    @app.command("diff")
    def diff_shortcut(
        remote: bool = typer.Option(False, "--remote"),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Show context changes."""
        sync_diff(remote=remote, fmt=fmt)

    @app.command("log")
    def log_shortcut(
        oneline: bool = typer.Option(False, "--oneline"),
        count: int = typer.Option(10, "-n"),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Show context change history."""
        sync_log(oneline=oneline, count=count, fmt=fmt)
