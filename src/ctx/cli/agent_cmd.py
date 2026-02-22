"""Agent-friendly interface: get, set, search, summary (top-level commands)."""

from __future__ import annotations

from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.core.dotpath import resolve_dotpath as _resolve_dotpath
from ctx.core.dotpath import set_dotpath as _set_dotpath
from ctx.utils.output import error, info, output


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
