"""State subcommands: show, set, clear."""

from __future__ import annotations

from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.utils.output import output, success

state_app = typer.Typer(no_args_is_help=True)


@state_app.command("show")
def state_show(fmt: Optional[str] = FORMAT_OPTION) -> None:
    """Show current session state."""
    store = get_store()
    state = store.read_active_state()
    if fmt == "json":
        output(state, fmt="json")
    else:
        from ctx.utils.output import console

        console.print(f"  Task: {state.current_task or '(none)'}")
        console.print(f"  Blockers: {', '.join(state.blockers) or '(none)'}")
        console.print(f"  Progress: {state.progress or '(none)'}")
        console.print(f"  Last agent: {state.last_agent or '(none)'}")
        console.print(f"  Last machine: {state.last_machine or '(none)'}")
        console.print(f"  Updated: {state.updated_at}")


@state_app.command("set")
def state_set(
    key: str = typer.Argument(..., help="State key (current_task, blockers, etc.)"),
    value: str = typer.Argument(..., help="Value to set"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Update a session state field."""
    store = get_store()
    state = store.read_active_state()

    if key == "current_task":
        state.current_task = value
    elif key == "blockers":
        # Comma-separated list
        state.blockers = [b.strip() for b in value.split(",") if b.strip()]
    elif key == "last_agent":
        state.last_agent = value
    elif key == "last_machine":
        state.last_machine = value
    else:
        # Store in progress dict as generic key
        state.progress[key] = value

    store.write_active_state(state)
    if fmt == "json":
        output({"key": key, "value": value, "status": "set"}, fmt="json")
    else:
        success(f"State '{key}' set to '{value}'")


@state_app.command("clear")
def state_clear(fmt: Optional[str] = FORMAT_OPTION) -> None:
    """Clear ephemeral session state and remove ephemeral entries."""
    store = get_store()
    from ctx.core.schema import ActiveState

    store.write_active_state(ActiveState())
    removed = store.clear_ephemeral()
    total_removed = sum(removed.values())
    if fmt == "json":
        output({"status": "cleared", "ephemeral_removed": removed}, fmt="json")
    else:
        success("Session state cleared")
        if total_removed > 0:
            from ctx.utils.output import console

            parts = []
            if removed["knowledge"]:
                parts.append(f"{removed['knowledge']} knowledge")
            if removed["decisions"]:
                parts.append(f"{removed['decisions']} decisions")
            if removed["skills"]:
                parts.append(f"{removed['skills']} skills")
            console.print(f"  Removed ephemeral entries: {', '.join(parts)}")
