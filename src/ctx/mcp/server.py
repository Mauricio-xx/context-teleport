"""MCP server exposing ContextStore as tools, resources, and prompts."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ctx.core.dotpath import resolve_dotpath, set_dotpath
from ctx.core.schema import SessionSummary
from ctx.core.scope import Scope
from ctx.core.search import search_files
from ctx.core.store import ContextStore
from ctx.sync.git_sync import GitSync, GitSyncError
from ctx.utils.paths import find_project_root

mcp = FastMCP(
    "context-teleport",
    instructions=(
        "Context Teleport provides portable, git-backed context for AI coding agents. "
        "Use resources to read project context and tools to modify it."
    ),
)

_store: ContextStore | None = None


def _get_store() -> ContextStore:
    """Return the module-level store, initializing from project root if needed."""
    global _store
    if _store is None:
        root = find_project_root()
        if root is None:
            raise RuntimeError("Not inside a project with a context store or git repo")
        _store = ContextStore(root)
    return _store


def set_store(store: ContextStore) -> None:
    """Override the module-level store (used in tests)."""
    global _store
    _store = store


def _parse_scope(value: str) -> Scope | None:
    """Parse a scope string, returning None for empty/invalid."""
    if not value:
        return None
    try:
        return Scope(value.lower())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Resources (read-only)
# ---------------------------------------------------------------------------


@mcp.resource("context://manifest")
def resource_manifest() -> str:
    """Project manifest with metadata and configuration."""
    store = _get_store()
    return store.read_manifest().model_dump_json(indent=2)


@mcp.resource("context://knowledge")
def resource_knowledge() -> str:
    """List all knowledge entries."""
    store = _get_store()
    entries = store.list_knowledge()
    return json.dumps(
        [
            {"key": e.key, "content": e.content, "scope": store.get_knowledge_scope(e.key).value}
            for e in entries
        ],
        indent=2,
        default=str,
    )


@mcp.resource("context://knowledge/{key}")
def resource_knowledge_item(key: str) -> str:
    """Read a specific knowledge entry by key."""
    store = _get_store()
    entry = store.get_knowledge(key)
    if entry is None:
        return json.dumps({"error": f"Knowledge entry '{key}' not found"})
    return json.dumps({"key": entry.key, "content": entry.content}, default=str)


@mcp.resource("context://decisions")
def resource_decisions() -> str:
    """List all architectural decisions."""
    store = _get_store()
    decisions = store.list_decisions()
    result = []
    for d in decisions:
        dec_scope = store.get_decision_scope(str(d.id))
        result.append({
            "id": d.id,
            "title": d.title,
            "status": d.status.value,
            "scope": dec_scope.value if dec_scope else "public",
        })
    return json.dumps(result, indent=2)


@mcp.resource("context://decisions/{id}")
def resource_decision_item(id: str) -> str:
    """Read a specific decision by ID or title."""
    store = _get_store()
    dec = store.get_decision(id)
    if dec is None:
        return json.dumps({"error": f"Decision '{id}' not found"})
    return json.dumps(
        {
            "id": dec.id,
            "title": dec.title,
            "status": dec.status.value,
            "context": dec.context,
            "decision": dec.decision,
            "consequences": dec.consequences,
        },
        indent=2,
    )


@mcp.resource("context://state")
def resource_state() -> str:
    """Current active session state."""
    store = _get_store()
    return store.read_active_state().model_dump_json(indent=2)


@mcp.resource("context://history")
def resource_history() -> str:
    """Recent session history."""
    store = _get_store()
    sessions = store.list_sessions()
    return json.dumps([s.model_dump() for s in sessions], indent=2, default=str)


@mcp.resource("context://summary")
def resource_summary() -> str:
    """High-level project context summary."""
    store = _get_store()
    return json.dumps(store.summary(), indent=2, default=str)


# ---------------------------------------------------------------------------
# Tools (mutations + queries)
# ---------------------------------------------------------------------------


@mcp.tool()
def context_search(query: str) -> str:
    """Search across all context files for a query string.

    Returns ranked results with file, key, line number, matching text, and relevance score.
    """
    store = _get_store()
    results = search_files(store.store_dir, query)
    return json.dumps(
        [
            {
                "key": r.key,
                "file": r.file,
                "line": r.line_number,
                "text": r.line,
                "score": r.score,
            }
            for r in results
        ],
        indent=2,
    )


@mcp.tool()
def context_add_knowledge(key: str, content: str, scope: str = "") -> str:
    """Add or update a knowledge entry.

    Args:
        key: Identifier for the entry (e.g. 'architecture', 'tech-stack')
        content: Markdown content for the entry
        scope: Optional scope (public/private/ephemeral). Empty means no change.
    """
    store = _get_store()
    scope_val = _parse_scope(scope)
    entry = store.set_knowledge(key, content, scope=scope_val)
    return json.dumps({"status": "ok", "key": entry.key}, default=str)


@mcp.tool()
def context_remove_knowledge(key: str) -> str:
    """Remove a knowledge entry by key.

    Args:
        key: Identifier of the entry to remove
    """
    store = _get_store()
    removed = store.rm_knowledge(key)
    if removed:
        return json.dumps({"status": "removed", "key": key})
    return json.dumps({"status": "not_found", "key": key})


@mcp.tool()
def context_record_decision(
    title: str,
    context: str = "",
    decision: str = "",
    consequences: str = "",
    scope: str = "",
) -> str:
    """Record an architectural decision (ADR-style).

    Args:
        title: Short decision title
        context: Why this decision was needed
        decision: What was decided
        consequences: Expected impact
        scope: Optional scope (public/private/ephemeral). Empty means public.
    """
    store = _get_store()
    scope_val = _parse_scope(scope)
    dec = store.add_decision(
        title=title,
        context=context,
        decision_text=decision,
        consequences=consequences,
        scope=scope_val,
    )
    return json.dumps(
        {"status": "ok", "id": dec.id, "title": dec.title}, default=str
    )


@mcp.tool()
def context_update_state(
    current_task: str = "",
    blockers: str = "",
) -> str:
    """Update the active session state.

    Args:
        current_task: What you are currently working on
        blockers: Comma-separated list of blockers (empty to clear)
    """
    store = _get_store()
    state = store.read_active_state()
    if current_task:
        state.current_task = current_task
    if blockers is not None:
        state.blockers = [b.strip() for b in blockers.split(",") if b.strip()]
    store.write_active_state(state)
    return json.dumps({"status": "ok", "current_task": state.current_task}, default=str)


@mcp.tool()
def context_append_session(
    agent: str = "",
    summary: str = "",
    knowledge_added: str = "",
    decisions_added: str = "",
) -> str:
    """Append a session summary to history.

    Args:
        agent: Agent identifier (e.g. 'claude-code', 'cursor')
        summary: Brief summary of what was done
        knowledge_added: Comma-separated list of knowledge keys added
        decisions_added: Comma-separated list of decision IDs added
    """
    store = _get_store()
    session = SessionSummary(
        agent=agent,
        summary=summary,
        knowledge_added=[k.strip() for k in knowledge_added.split(",") if k.strip()],
        decisions_added=[d.strip() for d in decisions_added.split(",") if d.strip()],
    )
    store.append_session(session)
    return json.dumps({"status": "ok", "session_id": session.id}, default=str)


@mcp.tool()
def context_sync_push(message: str = "") -> str:
    """Commit and push context changes to git remote.

    Args:
        message: Optional commit message (auto-generated if empty)
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
        result = gs.push(message=message or None)
        return json.dumps(result, default=str)
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def context_sync_pull() -> str:
    """Pull context changes from git remote."""
    store = _get_store()
    try:
        gs = GitSync(store.root)
        result = gs.pull()
        return json.dumps(result, default=str)
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def context_merge_status() -> str:
    """Check if there are unresolved merge conflicts."""
    store = _get_store()
    try:
        gs = GitSync(store.root)
        return json.dumps(gs.merge_status(), default=str)
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def context_resolve_conflict(file_path: str, content: str) -> str:
    """Resolve a single merge conflict by providing the final content.

    Args:
        file_path: Path of the conflicted file (relative to project root)
        content: Final resolved content for the file
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
        result = gs.resolve(file_path, content)
        return json.dumps(result, default=str)
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def context_get_scope(entry_type: str, key: str) -> str:
    """Get the current scope of a knowledge entry or decision.

    Args:
        entry_type: Either 'knowledge' or 'decision'
        key: The entry key (knowledge key or decision ID/title)
    """
    store = _get_store()
    if entry_type == "knowledge":
        entry = store.get_knowledge(key)
        if entry is None:
            return json.dumps({"error": f"Knowledge entry '{key}' not found"})
        scope = store.get_knowledge_scope(key)
        return json.dumps({"key": key, "scope": scope.value})
    elif entry_type == "decision":
        scope = store.get_decision_scope(key)
        if scope is None:
            return json.dumps({"error": f"Decision '{key}' not found"})
        return json.dumps({"key": key, "scope": scope.value})
    else:
        return json.dumps({"error": f"Invalid entry_type '{entry_type}'. Use 'knowledge' or 'decision'."})


@mcp.tool()
def context_set_scope(entry_type: str, key: str, scope: str) -> str:
    """Change the scope of a knowledge entry or decision.

    Args:
        entry_type: Either 'knowledge' or 'decision'
        key: The entry key (knowledge key or decision ID/title)
        scope: New scope (public/private/ephemeral)
    """
    store = _get_store()
    scope_val = _parse_scope(scope)
    if scope_val is None:
        return json.dumps({"error": f"Invalid scope '{scope}'. Use public, private, or ephemeral."})

    if entry_type == "knowledge":
        if store.set_knowledge_scope(key, scope_val):
            return json.dumps({"status": "ok", "key": key, "scope": scope_val.value})
        return json.dumps({"error": f"Knowledge entry '{key}' not found"})
    elif entry_type == "decision":
        if store.set_decision_scope(key, scope_val):
            return json.dumps({"status": "ok", "key": key, "scope": scope_val.value})
        return json.dumps({"error": f"Decision '{key}' not found"})
    else:
        return json.dumps({"error": f"Invalid entry_type '{entry_type}'. Use 'knowledge' or 'decision'."})


@mcp.tool()
def context_get(dotpath: str) -> str:
    """Read any value by dotpath.

    Examples: 'knowledge.architecture', 'decisions.1', 'state', 'manifest.project.name'

    Args:
        dotpath: Dot-separated path to the value
    """
    store = _get_store()
    value = resolve_dotpath(store, dotpath)
    if value is None:
        return json.dumps({"error": f"No value at '{dotpath}'"})
    return json.dumps(value, indent=2, default=str)


@mcp.tool()
def context_set(dotpath: str, value: str) -> str:
    """Set a value by dotpath.

    Examples: 'knowledge.architecture', 'state.current_task', 'preferences.team.style'

    Args:
        dotpath: Dot-separated path to the value
        value: Value to set
    """
    store = _get_store()
    try:
        set_dotpath(store, dotpath, value)
        return json.dumps({"status": "ok", "dotpath": dotpath})
    except ValueError as e:
        return json.dumps({"status": "error", "error": str(e)})


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def context_onboarding() -> str:
    """Full project context for a new agent session.

    Provides the public knowledge base, decisions, current state,
    and recent history to quickly onboard a new agent.
    """
    store = _get_store()
    manifest = store.read_manifest()
    knowledge = store.list_knowledge(scope=Scope.public)
    decisions = store.list_decisions(scope=Scope.public)
    state = store.read_active_state()
    sessions = store.list_sessions(limit=5)

    lines = [
        f"# Project: {manifest.project.name}",
        f"Schema version: {manifest.schema_version}",
        "",
    ]

    if knowledge:
        lines.append("## Knowledge Base")
        lines.append("")
        for entry in knowledge:
            lines.append(f"### {entry.key}")
            lines.append(entry.content.strip())
            lines.append("")

    if decisions:
        lines.append("## Architectural Decisions")
        lines.append("")
        for d in decisions:
            lines.append(f"### ADR-{d.id:04d}: {d.title} ({d.status.value})")
            if d.context:
                lines.append(f"**Context:** {d.context}")
            if d.decision:
                lines.append(f"**Decision:** {d.decision}")
            if d.consequences:
                lines.append(f"**Consequences:** {d.consequences}")
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

    return "\n".join(lines)


@mcp.prompt()
def context_handoff() -> str:
    """Session handoff summary for the next agent.

    Provides current state, recent changes, and any blockers
    to enable a smooth session transition.
    """
    store = _get_store()
    state = store.read_active_state()
    sessions = store.list_sessions(limit=3)

    lines = ["# Session Handoff", ""]

    lines.append("## Current State")
    if state.current_task:
        lines.append(f"- Working on: {state.current_task}")
    else:
        lines.append("- No active task")
    if state.blockers:
        lines.append(f"- Blockers: {', '.join(state.blockers)}")
    if state.progress:
        lines.append("- Progress:")
        for k, v in state.progress.items():
            lines.append(f"  - {k}: {v}")
    lines.append("")

    if sessions:
        lines.append("## Recent Sessions")
        for s in sessions:
            agent_label = f"[{s.agent}]" if s.agent else ""
            lines.append(f"- {agent_label} {s.summary}")
        lines.append("")

    return "\n".join(lines)


@mcp.prompt()
def context_review_decisions() -> str:
    """All architectural decisions with their status.

    Use this to review past decisions before making new ones.
    """
    store = _get_store()
    decisions = store.list_decisions()

    if not decisions:
        return "No decisions recorded yet."

    lines = ["# Architectural Decisions Review", ""]
    for d in decisions:
        lines.append(f"## ADR-{d.id:04d}: {d.title}")
        lines.append(f"**Status:** {d.status.value}")
        lines.append(f"**Date:** {d.date.strftime('%Y-%m-%d')}")
        if d.author:
            lines.append(f"**Author:** {d.author}")
        lines.append("")
        if d.context:
            lines.append(f"### Context\n{d.context}")
            lines.append("")
        if d.decision:
            lines.append(f"### Decision\n{d.decision}")
            lines.append("")
        if d.consequences:
            lines.append(f"### Consequences\n{d.consequences}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Run the MCP server on stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
