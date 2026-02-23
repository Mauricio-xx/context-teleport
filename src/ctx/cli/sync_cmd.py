"""Sync subcommands: push, pull, diff, log, resolve. Also registers top-level shortcuts."""

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
def sync_pull(
    strategy: str = typer.Option("ours", "--strategy", "-s", help="Merge strategy: ours, theirs, interactive, agent"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Pull remote context and merge."""
    store = get_store()
    from ctx.core.conflicts import Strategy
    from ctx.sync.git_sync import GitSync

    try:
        strat = Strategy(strategy)
    except ValueError:
        error(f"Invalid strategy: {strategy}. Use: ours, theirs, interactive, agent")
        raise typer.Exit(1)

    gs = GitSync(store.root)
    result = gs.pull(strategy=strat)

    # Interactive strategy: walk the user through each conflict
    if result.get("status") == "conflicts" and strat == Strategy.interactive:
        from ctx.cli.interactive import interactive_resolve
        from ctx.utils.output import is_piped

        if is_piped():
            info("Non-interactive mode detected, falling back to 'ours' strategy")
            result = gs.pull(strategy=Strategy.ours)
        else:
            resolutions = interactive_resolve(gs._pending_report)
            if resolutions:
                result = gs.apply_resolutions(resolutions)
            else:
                info("No resolutions applied (all skipped)")
                if fmt == "json":
                    output(result, fmt="json")
                return

    if fmt == "json":
        output(result, fmt="json")
    else:
        status = result.get("status")
        if status == "pulled":
            success(f"Context pulled and merged ({result.get('commits', 0)} commits)")
        elif status == "merged":
            resolved = result.get("resolved", 0)
            skipped = result.get("skipped", 0)
            detail = f"{resolved} resolved"
            if skipped:
                detail += f", {skipped} skipped (kept ours)"
            success(f"Context merged with strategy '{strategy}' ({detail})")
        elif status == "up_to_date":
            info("Already up to date")
        elif status == "conflicts":
            report = result.get("report", {})
            error(f"Merge conflicts detected: {report.get('unresolved', 0)} unresolved")
            for c in report.get("conflicts", []):
                info(f"  {c['file_path']}")
            info("Resolve with: ctx sync resolve --strategy ours|theirs")
        else:
            error(result.get("error", "Pull failed"))


@sync_app.command("resolve")
def sync_resolve(
    strategy: str = typer.Option("ours", "--strategy", "-s", help="Resolution strategy: ours, theirs"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Resolve pending merge conflicts by retrying pull with the given strategy.

    Only supports 'ours' and 'theirs'. For interactive resolution, use
    `ctx pull --strategy interactive` which handles the full TUI flow.
    """
    store = get_store()
    from ctx.core.conflicts import Strategy
    from ctx.sync.git_sync import GitSync

    if strategy not in ("ours", "theirs"):
        error(f"Invalid strategy: {strategy}. Use: ours, theirs")
        info("For interactive resolution, use: ctx pull --strategy interactive")
        raise typer.Exit(1)

    try:
        strat = Strategy(strategy)
    except ValueError:
        error(f"Invalid strategy: {strategy}. Use: ours, theirs")
        raise typer.Exit(1)

    gs = GitSync(store.root)
    status_info = gs.merge_status()
    if status_info.get("status") == "clean":
        info("No conflicts to resolve")
        return

    # Retry pull with the chosen strategy
    result = gs.pull(strategy=strat)

    if fmt == "json":
        output(result, fmt="json")
    else:
        res_status = result.get("status")
        if res_status == "merged":
            success(f"Resolved {result.get('resolved', 0)} conflicts with strategy '{strategy}'")
        elif res_status == "pulled":
            success("Context pulled and merged (conflicts resolved upstream)")
        elif res_status == "conflicts":
            report = result.get("report", {})
            error(f"Still {report.get('unresolved', 0)} unresolved conflicts")
        else:
            error(result.get("error", "Resolution failed"))


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
    def pull_shortcut(
        strategy: str = typer.Option("ours", "--strategy", "-s"),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Pull remote context and merge."""
        sync_pull(strategy=strategy, fmt=fmt)

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
