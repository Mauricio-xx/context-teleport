"""Skill subcommands: list, get, add, rm, scope."""

from __future__ import annotations

import sys
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.core.frontmatter import build_frontmatter, parse_frontmatter
from ctx.core.scope import Scope
from ctx.utils.output import error, info, output, output_table, success

skill_app = typer.Typer(no_args_is_help=True)


def _parse_scope(value: str) -> Scope | None:
    if not value:
        return None
    try:
        return Scope(value.lower())
    except ValueError:
        return None


@skill_app.command("list")
def skill_list(
    scope: Optional[str] = typer.Option(None, "--scope", "-s", help="Filter by scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """List available skills."""
    store = get_store()
    scope_filter = _parse_scope(scope) if scope else None
    entries = store.list_skills(scope=scope_filter)
    if fmt == "json":
        items = []
        for e in entries:
            items.append({
                "name": e.name,
                "description": e.description,
                "scope": store.get_skill_scope(e.name).value,
            })
        output(items, fmt="json")
    else:
        if not entries:
            info("No skills yet. Use `context-teleport skill add <name>` to add one.")
            return
        rows = []
        for e in entries:
            rows.append({
                "name": e.name,
                "description": e.description[:60],
                "scope": store.get_skill_scope(e.name).value,
            })
        output_table(rows, columns=["name", "description", "scope"])


@skill_app.command("get")
def skill_get(
    name: str = typer.Argument(..., help="Skill name"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Print full SKILL.md content."""
    store = get_store()
    entry = store.get_skill(name)
    if entry is None:
        error(f"Skill '{name}' not found")
        raise typer.Exit(1)
    if fmt == "json":
        output({"name": entry.name, "description": entry.description, "content": entry.content}, fmt="json")
    else:
        output(entry.content, title=entry.name)


@skill_app.command("add")
def skill_add(
    name: str = typer.Argument(..., help="Skill name (used as directory name)"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read SKILL.md content from file"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Skill description (for auto-generated frontmatter)"),
    scope: Optional[str] = typer.Option(None, "--scope", "-s", help="Scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Create or update a skill from file, stdin, or editor template."""
    store = get_store()

    if file:
        from pathlib import Path

        text = Path(file).read_text()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        # Generate a template if no input provided
        desc = description or f"Description for {name}"
        text = build_frontmatter(
            {"name": name, "description": desc},
            f"# {name}\n\nInstructions for this skill go here.\n",
        )

    # Ensure frontmatter has name field
    meta, body = parse_frontmatter(text)
    if "name" not in meta:
        meta["name"] = name
        if description and "description" not in meta:
            meta["description"] = description or ""
        text = build_frontmatter(meta, body)

    scope_val = _parse_scope(scope) if scope else None
    entry = store.set_skill(name, text, scope=scope_val)
    if fmt == "json":
        output({"name": entry.name, "status": "written"}, fmt="json")
    else:
        success(f"Skill '{entry.name}' written")


@skill_app.command("rm")
def skill_rm(
    name: str = typer.Argument(..., help="Skill name"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Remove a skill."""
    store = get_store()
    if store.rm_skill(name):
        if fmt == "json":
            output({"name": name, "status": "removed"}, fmt="json")
        else:
            success(f"Skill '{name}' removed")
    else:
        error(f"Skill '{name}' not found")
        raise typer.Exit(1)


@skill_app.command("scope")
def skill_scope(
    name: str = typer.Argument(..., help="Skill name"),
    scope: str = typer.Argument(..., help="New scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Change the scope of an existing skill."""
    store = get_store()
    scope_val = _parse_scope(scope)
    if scope_val is None:
        error(f"Invalid scope '{scope}'. Use public, private, or ephemeral.")
        raise typer.Exit(1)

    if store.set_skill_scope(name, scope_val):
        if fmt == "json":
            output({"name": name, "scope": scope_val.value, "status": "updated"}, fmt="json")
        else:
            success(f"Skill '{name}' scope set to {scope_val.value}")
    else:
        error(f"Skill '{name}' not found")
        raise typer.Exit(1)
