"""MCP server exposing ContextStore as tools, resources, and prompts."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from ctx.core.conflicts import Strategy, resolve_single
from ctx.core.dotpath import resolve_dotpath, set_dotpath
from ctx.core.schema import SessionSummary
from ctx.core.scope import Scope
from ctx.core.search import search_files
from ctx.core.store import ContextStore
from ctx.sync.git_sync import GitSync, GitSyncError
from ctx.utils.paths import find_project_root

logger = logging.getLogger(__name__)

_FALLBACK_INSTRUCTIONS = (
    "Context Teleport provides portable, git-backed context for AI coding agents. "
    "Use resources to read project context and tools to modify it."
)


def _generate_instructions() -> str:
    """Build a concise instruction string from the current store state.

    Returns a project-aware summary when a store is available,
    falling back to generic instructions on any error.
    """
    try:
        store = _get_store()
        if not store.initialized:
            return _FALLBACK_INSTRUCTIONS

        manifest = store.read_manifest()
        project_name = manifest.project.name
        knowledge = store.list_knowledge()
        decisions = store.list_decisions()
        state = store.read_active_state()

        lines = [
            f"Context Teleport is active for project '{project_name}'.",
            "",
        ]

        if knowledge:
            keys = [e.key for e in knowledge]
            lines.append(f"Knowledge base ({len(keys)} entries): {', '.join(keys)}.")

        if decisions:
            lines.append(f"Architectural decisions: {len(decisions)} recorded.")

        if state.current_task:
            lines.append(f"Current task: {state.current_task}")

        if state.blockers:
            lines.append(f"Blockers: {', '.join(state.blockers)}")

        lines.extend([
            "",
            "Use context_onboarding prompt for full project context. "
            "Use tools to read/write knowledge, decisions, and state. "
            "Use context_sync_push/pull to sync changes via git.",
        ])

        return "\n".join(lines)
    except Exception:
        return _FALLBACK_INSTRUCTIONS


@asynccontextmanager
async def _server_lifespan(app: FastMCP) -> AsyncIterator[None]:
    """MCP server lifespan: best-effort push on shutdown."""
    try:
        yield
    finally:
        try:
            store = _get_store()
            gs = GitSync(store.root)
            if gs._has_changes():
                gs.push()
        except Exception:
            logger.debug("Shutdown push skipped (no store or git)")


mcp = FastMCP(
    "context-teleport",
    instructions=_FALLBACK_INSTRUCTIONS,
    lifespan=_server_lifespan,
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


def _get_agent_name() -> str:
    """Detect the calling agent's identity.

    Checks MCP_CALLER environment variable first, then falls back to generic.
    Individual adapters set MCP_CALLER when they register.
    """
    import os
    return os.environ.get("MCP_CALLER", "mcp:unknown")


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
    author = _get_agent_name()
    entry = store.set_knowledge(key, content, author=author, scope=scope_val)
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
    author = _get_agent_name()
    dec = store.add_decision(
        title=title,
        context=context,
        decision_text=decision,
        consequences=consequences,
        author=author,
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
def context_sync_pull(strategy: str = "ours") -> str:
    """Pull context changes from git remote.

    Args:
        strategy: Conflict resolution strategy. Use 'agent' to inspect and resolve
                  conflicts via context_conflict_detail / context_resolve_conflict /
                  context_merge_finalize. Options: ours, theirs, agent.
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
        try:
            strat = Strategy(strategy.lower())
        except ValueError:
            return json.dumps({"status": "error", "error": f"Invalid strategy '{strategy}'. Use: ours, theirs, agent."})
        result = gs.pull(strategy=strat)
        return json.dumps(result, default=str)
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def context_merge_status() -> str:
    """Check if there are unresolved merge conflicts.

    Reads from disk-persisted conflict state (survives across MCP calls).
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
        report = gs.load_pending_report()
        if report is None:
            return json.dumps({"status": "clean"})
        return json.dumps({
            "status": "conflicts",
            "conflict_id": report.conflict_id,
            "report": report.to_dict(),
        }, default=str)
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def context_resolve_conflict(file_path: str, content: str) -> str:
    """Resolve a single merge conflict by providing the final content.

    The resolution is persisted to disk. Call context_merge_finalize when all
    conflicts are resolved to complete the merge.

    Args:
        file_path: Path of the conflicted file (relative to project root)
        content: Final resolved content for the file
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
        report = gs.load_pending_report()
        if report is None:
            return json.dumps({"status": "error", "error": "No pending conflicts"})

        found = resolve_single(report, file_path, content)
        if not found:
            return json.dumps({"status": "error", "error": f"No unresolved conflict for {file_path}"})

        gs.save_pending_report(report)
        return json.dumps({
            "status": "resolved",
            "file_path": file_path,
            "remaining": report.unresolved_count,
        }, default=str)
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
def context_conflict_detail(file_path: str) -> str:
    """Get detailed conflict information for a single file.

    Returns full ours/theirs/base content, a unified diff, and section-level
    analysis for markdown files. Use this to examine each conflict before
    resolving it with context_resolve_conflict.

    Args:
        file_path: Path of the conflicted file (relative to project root)
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
        report = gs.load_pending_report()
        if report is None:
            return json.dumps({"status": "error", "error": "No pending conflicts"})

        entry = None
        for c in report.conflicts:
            if c.file_path == file_path and not c.resolved:
                entry = c
                break

        if entry is None:
            return json.dumps({"status": "error", "error": f"No unresolved conflict for {file_path}"})

        import difflib
        diff = "\n".join(difflib.unified_diff(
            entry.ours_content.splitlines(),
            entry.theirs_content.splitlines(),
            fromfile=f"{file_path} (ours)",
            tofile=f"{file_path} (theirs)",
            lineterm="",
        ))

        result: dict = {
            "file_path": entry.file_path,
            "ours_content": entry.ours_content,
            "theirs_content": entry.theirs_content,
            "base_content": entry.base_content,
            "diff": diff,
        }

        if file_path.endswith(".md") and entry.base_content:
            from ctx.core.merge_sections import merge_markdown_sections
            section_result = merge_markdown_sections(
                entry.base_content, entry.ours_content, entry.theirs_content,
            )
            result["section_analysis"] = {
                "has_section_conflicts": section_result.has_conflicts,
                "conflict_details": section_result.conflict_details,
                "auto_merged_content": section_result.content if not section_result.has_conflicts else None,
            }

        return json.dumps(result, default=str)
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def context_merge_finalize() -> str:
    """Finalize the merge after resolving all (or some) conflicts.

    Applies resolved content to files, falls back to 'ours' for any
    unresolved files, and commits the merge. Clears pending conflict state.
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
        report = gs.load_pending_report()
        if report is None:
            return json.dumps({"status": "error", "error": "No pending conflicts to finalize"})

        resolutions = [
            (c.file_path, c.resolution)
            for c in report.conflicts
            if c.resolved
        ]

        result = gs.apply_resolutions(resolutions)
        return json.dumps(result, default=str)
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def context_merge_abort() -> str:
    """Abort the pending merge and discard conflict state.

    Cleans up the pending conflicts file without merging.
    The next pull will re-detect conflicts.
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
        if not gs.has_pending_conflicts():
            return json.dumps({"status": "error", "error": "No pending conflicts to abort"})
        gs.clear_pending_report()
        return json.dumps({"status": "aborted"})
    except GitSyncError as e:
        return json.dumps({"status": "error", "error": str(e)})


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


@mcp.prompt()
def context_resolve_conflicts() -> str:
    """Guide for resolving merge conflicts via MCP tools.

    Provides conflict overview, per-file summary, and step-by-step instructions
    for the agent to resolve conflicts using the available MCP tools.
    """
    store = _get_store()
    try:
        gs = GitSync(store.root)
    except GitSyncError:
        return "Error: not in a git repository."

    report = gs.load_pending_report()
    if report is None:
        return "No pending merge conflicts. Use context_sync_pull(strategy='agent') to pull with conflict detection."

    lines = [
        "# Merge Conflict Resolution Guide",
        "",
        f"**Conflict ID:** {report.conflict_id}",
        f"**Total conflicts:** {len(report.conflicts)}",
        f"**Unresolved:** {report.unresolved_count}",
        f"**Auto-resolved:** {len(report.auto_resolved)}",
        "",
        "## Conflicted Files",
        "",
    ]

    for c in report.conflicts:
        status = "resolved" if c.resolved else "UNRESOLVED"
        is_md = "markdown" if c.file_path.endswith(".md") else "other"
        lines.append(
            f"- `{c.file_path}` [{status}] ({is_md}, "
            f"ours: {len(c.ours_content)} chars, theirs: {len(c.theirs_content)} chars)"
        )

    lines.extend([
        "",
        "## Resolution Steps",
        "",
        "1. **Examine each file:** Call `context_conflict_detail(file_path)` for each unresolved file",
        "2. **Resolve:** Call `context_resolve_conflict(file_path, content)` with the merged content",
        "3. **Finalize:** Call `context_merge_finalize()` to commit the merge",
        "",
        "## Merge Guidelines",
        "",
        "- **Combine knowledge:** merge complementary information from both sides",
        "- **Never drop decisions:** if both sides added different ADRs, keep both",
        "- **Prefer newer data:** for state/progress fields, the more recent update wins",
        "- **Preserve structure:** maintain section headers and formatting",
        "- If section_analysis shows no conflicts, use the auto_merged_content directly",
        "",
        "To abort the merge instead: call `context_merge_abort()`",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Run the MCP server on stdio."""
    mcp._mcp_server.instructions = _generate_instructions()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
