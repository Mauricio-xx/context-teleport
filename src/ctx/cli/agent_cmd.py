"""Agent-friendly interface: get, set, search, summary (top-level commands)."""

from __future__ import annotations

import json
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.utils.output import error, info, output, success


def _resolve_dotpath(store, dotpath: str):
    """Resolve a dotpath like 'knowledge.architecture' into a value."""
    parts = dotpath.split(".")

    if not parts:
        return None

    section = parts[0]
    rest = parts[1:]

    if section == "knowledge":
        if not rest:
            entries = store.list_knowledge()
            return {e.key: e.content for e in entries}
        key = rest[0]
        entry = store.get_knowledge(key)
        if entry is None:
            return None
        return entry.content

    elif section == "decisions":
        if not rest:
            decisions = store.list_decisions()
            return [
                {"id": d.id, "title": d.title, "status": d.status.value}
                for d in decisions
            ]
        dec = store.get_decision(rest[0])
        if dec is None:
            return None
        if len(rest) > 1:
            return getattr(dec, rest[1], None)
        return {
            "id": dec.id,
            "title": dec.title,
            "status": dec.status.value,
            "context": dec.context,
            "decision": dec.decision,
            "consequences": dec.consequences,
        }

    elif section == "state":
        state = store.read_active_state()
        if not rest:
            return state.model_dump()
        return getattr(state, rest[0], state.progress.get(rest[0]))

    elif section == "preferences":
        if rest and rest[0] == "team":
            prefs = store.read_team_preferences()
            if len(rest) > 1:
                return prefs.values.get(rest[1])
            return prefs.values
        elif rest and rest[0] == "user":
            prefs = store.read_user_preferences()
            if len(rest) > 1:
                return prefs.values.get(rest[1])
            return prefs.values
        return {
            "team": store.read_team_preferences().values,
            "user": store.read_user_preferences().values,
        }

    elif section == "manifest":
        manifest = store.read_manifest()
        data = manifest.model_dump()
        obj = data
        for p in rest:
            if isinstance(obj, dict):
                obj = obj.get(p)
            else:
                return None
        return obj

    elif section == "history":
        sessions = store.list_sessions()
        return [s.model_dump() for s in sessions]

    return None


def _set_dotpath(store, dotpath: str, value: str):
    """Set a value at a dotpath."""
    parts = dotpath.split(".")

    if not parts:
        raise ValueError("Empty dotpath")

    section = parts[0]
    rest = parts[1:]

    if section == "knowledge":
        if not rest:
            raise ValueError("Specify a knowledge key: knowledge.<key>")
        store.set_knowledge(rest[0], value)
        return

    if section == "state":
        state = store.read_active_state()
        if not rest:
            raise ValueError("Specify a state field: state.<field>")
        field = rest[0]
        if field == "current_task":
            state.current_task = value
        elif field == "blockers":
            state.blockers = [b.strip() for b in value.split(",") if b.strip()]
        elif field == "last_agent":
            state.last_agent = value
        elif field == "last_machine":
            state.last_machine = value
        else:
            state.progress[field] = value
        store.write_active_state(state)
        return

    if section == "preferences":
        if not rest:
            raise ValueError("Specify preferences.team.<key> or preferences.user.<key>")
        if rest[0] == "team":
            prefs = store.read_team_preferences()
            if len(rest) > 1:
                prefs.values[rest[1]] = value
            store.write_team_preferences(prefs)
        elif rest[0] == "user":
            prefs = store.read_user_preferences()
            if len(rest) > 1:
                prefs.values[rest[1]] = value
            store.write_user_preferences(prefs)
        return

    raise ValueError(f"Cannot set values in section '{section}'")


def register_agent_commands(app: typer.Typer) -> None:
    """Register get, set, search, summary as top-level commands."""

    @app.command("get")
    def agent_get(
        dotpath: str = typer.Argument(..., help="Dotpath (e.g. knowledge.architecture)"),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Read any value by dotpath (JSON to stdout)."""
        store = get_store()
        value = _resolve_dotpath(store, dotpath)
        if value is None:
            error(f"No value at '{dotpath}'")
            raise typer.Exit(1)
        # Agent commands always default to json
        out_fmt = fmt or "json"
        output(value, fmt=out_fmt)

    @app.command("set")
    def agent_set(
        dotpath: str = typer.Argument(..., help="Dotpath (e.g. knowledge.architecture)"),
        value: str = typer.Argument(..., help="Value to set"),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Write any value by dotpath."""
        store = get_store()
        try:
            _set_dotpath(store, dotpath, value)
            out_fmt = fmt or "json"
            output({"dotpath": dotpath, "status": "set"}, fmt=out_fmt)
        except ValueError as e:
            error(str(e))
            raise typer.Exit(1)

    @app.command("search")
    def agent_search(
        query: str = typer.Argument(..., help="Search query"),
        json_output: bool = typer.Option(False, "--json", help="Force JSON output"),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Search across all context with optional JSON output."""
        store = get_store()
        from ctx.core.search import search_files

        results = search_files(store.store_dir, query)
        out_fmt = fmt or ("json" if json_output else None)
        if out_fmt == "json":
            output(
                [{"key": r.key, "file": r.file, "line": r.line_number, "text": r.line, "score": r.score}
                 for r in results],
                fmt="json",
            )
        else:
            from ctx.utils.output import output_table

            if not results:
                info(f"No results for '{query}'")
                return
            output_table(
                [{"key": r.key, "line": str(r.line_number), "match": r.line[:80]} for r in results[:20]],
                columns=["key", "line", "match"],
            )

    @app.command("summary")
    def agent_summary(fmt: Optional[str] = FORMAT_OPTION) -> None:
        """One-page context summary optimized for LLM context windows."""
        store = get_store()
        manifest = store.read_manifest()
        knowledge = store.list_knowledge()
        decisions = store.list_decisions()
        state = store.read_active_state()
        sessions = store.list_sessions(limit=5)

        if fmt == "json":
            output(store.summary(), fmt="json")
            return

        lines = [
            f"# {manifest.project.name} -- Context Summary",
            "",
        ]

        if knowledge:
            lines.append("## Knowledge")
            lines.append("")
            for entry in knowledge:
                lines.append(f"### {entry.key}")
                lines.append(entry.content.strip())
                lines.append("")

        if decisions:
            lines.append("## Decisions")
            lines.append("")
            for d in decisions:
                lines.append(f"- **{d.id:04d}** {d.title} ({d.status.value})")
            lines.append("")

        if state.current_task:
            lines.append("## Current State")
            lines.append(f"- Task: {state.current_task}")
            if state.blockers:
                lines.append(f"- Blockers: {', '.join(state.blockers)}")
            lines.append("")

        if sessions:
            lines.append("## Recent Sessions")
            for s in sessions:
                lines.append(f"- [{s.agent}] {s.summary}")
            lines.append("")

        from ctx.utils.output import console

        console.print("\n".join(lines))
