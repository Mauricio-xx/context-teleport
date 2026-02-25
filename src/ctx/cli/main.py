"""Typer app: top-level command groups and root commands (init, status)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.core.store import ContextStore, StoreError
from ctx.utils.output import error, info, output, success
from ctx.utils.paths import find_project_root

app = typer.Typer(
    name="context-teleport",
    help="Context Teleport: portable, git-backed context store for AI coding agents.",
    no_args_is_help=True,
)


@app.command()
def init(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name"),
    repo_url: str = typer.Option("", "--repo-url", help="Git remote URL"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Initialize context store in current project."""
    root = find_project_root() or Path.cwd()
    store = ContextStore(root)
    try:
        manifest = store.init(project_name=name, repo_url=repo_url)
        if fmt == "json":
            output(manifest, fmt="json")
        else:
            success(f"Initialized context store for '{manifest.project.name}' at {store.store_dir}")
    except StoreError as e:
        error(str(e))
        raise typer.Exit(1)


@app.command()
def status(fmt: Optional[str] = FORMAT_OPTION) -> None:
    """Show store state, sync status, adapter info."""
    try:
        store = get_store()
        if not store.initialized:
            error("Context store not initialized. Run `context-teleport init` first.")
            raise typer.Exit(1)

        summary_data = store.summary()
        manifest = store.read_manifest()

        if fmt == "json":
            output(summary_data, fmt="json")
        else:
            from rich.panel import Panel
            from ctx.utils.output import console

            console.print(Panel(f"[bold]{manifest.project.name}[/bold]", title="Context Teleport"))
            console.print(f"  Schema version: {manifest.schema_version}")
            console.print(f"  Store: {store.store_dir}")
            console.print(f"  Knowledge entries: {summary_data['knowledge_count']}")
            if summary_data["knowledge_keys"]:
                console.print(f"    Keys: {', '.join(summary_data['knowledge_keys'])}")
            console.print(f"  Decisions: {summary_data['decision_count']}")
            console.print(f"  Skills: {summary_data['skill_count']}")
            if summary_data["skill_names"]:
                console.print(f"    Names: {', '.join(summary_data['skill_names'])}")
            if summary_data["current_task"]:
                console.print(f"  Current task: {summary_data['current_task']}")
            if summary_data["blockers"]:
                console.print(f"  Blockers: {', '.join(summary_data['blockers'])}")

            adapters = manifest.adapters
            if adapters:
                console.print("  Adapters:")
                for adapter_name, cfg in adapters.items():
                    status_str = "[green]enabled[/green]" if cfg.enabled else "[dim]disabled[/dim]"
                    console.print(f"    {adapter_name}: {status_str}")

    except StoreError as e:
        error(str(e))
        raise typer.Exit(1)


# Register subcommand groups
from ctx.cli.knowledge_cmd import knowledge_app
from ctx.cli.decision_cmd import decision_app
from ctx.cli.state_cmd import state_app
from ctx.cli.sync_cmd import sync_app, register_sync_shortcuts
from ctx.cli.adapter_cmd import adapter_app, export_app, register_mcp_commands
from ctx.cli.agent_cmd import register_agent_commands
from ctx.cli.skill_cmd import skill_app
from ctx.cli.config_cmd import config_app
from ctx.cli.watch_cmd import watch_command

app.add_typer(knowledge_app, name="knowledge", help="Manage knowledge entries")
app.add_typer(decision_app, name="decision", help="Manage decision records (ADR)")
app.add_typer(state_app, name="state", help="Manage session state")
app.add_typer(sync_app, name="sync", help="Git-backed sync commands")
app.add_typer(adapter_app, name="import", help="Import from adapters/bundles")
app.add_typer(export_app, name="export", help="Export to adapters/bundles")
app.add_typer(skill_app, name="skill", help="Manage agent skills (SKILL.md)")
app.add_typer(config_app, name="config", help="Manage global configuration")

register_agent_commands(app)
register_sync_shortcuts(app)
register_mcp_commands(app)
app.command("watch")(watch_command)
