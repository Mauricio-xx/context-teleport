"""Import/export subcommands: adapter operations, bundle I/O, MCP registration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.utils.output import error, info, output, success

adapter_app = typer.Typer(no_args_is_help=True)
export_app = typer.Typer(no_args_is_help=True)

# Tool name to adapter registry key mapping
_TOOL_MAP: dict[str, str] = {
    "claude-code": "claude_code",
    "opencode": "opencode",
    "codex": "codex",
    "gemini": "gemini",
    "cursor": "cursor",
}


def _import_adapter(adapter_name: str, label: str, dry_run: bool, fmt: str | None) -> None:
    """Generic import handler for any adapter."""
    store = get_store()
    from ctx.adapters.registry import get_adapter

    adapter = get_adapter(adapter_name, store)
    if adapter is None:
        error(f"Unknown adapter: {adapter_name}")
        raise typer.Exit(1)

    result = adapter.import_context(dry_run=dry_run)
    if fmt == "json":
        output(result, fmt="json")
    elif dry_run:
        info("Dry run -- the following would be imported:")
        for item in result.get("items", []):
            info(f"  {item.get('type', 'item')}: {item.get('key', '?')} ({item.get('source', '?')})")
    else:
        imported = result.get("imported", 0)
        if imported:
            success(f"Imported {imported} items from {label}")
        else:
            info(f"Nothing to import from {label}")


def _export_adapter(adapter_name: str, label: str, dry_run: bool, fmt: str | None) -> None:
    """Generic export handler for any adapter."""
    store = get_store()
    from ctx.adapters.registry import get_adapter

    adapter = get_adapter(adapter_name, store)
    if adapter is None:
        error(f"Unknown adapter: {adapter_name}")
        raise typer.Exit(1)

    result = adapter.export_context(dry_run=dry_run)
    if fmt == "json":
        output(result, fmt="json")
    elif dry_run:
        info("Dry run -- the following would be exported:")
        for item in result.get("items", []):
            info(f"  {item.get('target', '?')}: {item.get('description', '?')}")
    else:
        exported = result.get("exported", 0)
        if exported:
            success(f"Exported {exported} items to {label}")
        else:
            info("Nothing to export")


def register_mcp_commands(app: typer.Typer) -> None:
    """Register top-level `context-teleport register` and `context-teleport unregister` commands."""

    @app.command("register")
    def register_cmd(
        tool: Optional[str] = typer.Argument(
            None,
            help="Tool name (auto-detect if omitted). Options: claude-code, opencode, codex, gemini, cursor",
        ),
        local: bool = typer.Option(
            False,
            "--local",
            help="Use local context-teleport command instead of uvx (for development)",
        ),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Register context-teleport MCP server. Auto-detects available tools or specify one."""
        store = get_store()
        from ctx.adapters.registry import detect_adapters, get_adapter

        if tool is not None:
            adapter_key = _TOOL_MAP.get(tool, tool.replace("-", "_"))
            adapter = get_adapter(adapter_key, store)
            if adapter is None:
                error(f"Unknown tool: {tool}")
                raise typer.Exit(1)
            result = adapter.register_mcp(local=local)
            if fmt == "json":
                output(result, fmt="json")
            elif result["status"] == "registered":
                success(f"MCP server registered for {tool}")
            elif result["status"] == "unsupported":
                info(f"MCP registration not supported for {tool}")
            else:
                info(f"MCP registration: {result['status']}")
        else:
            # Auto-detect: register for all detected tools
            detected = detect_adapters(store)
            registered = []
            for name, available in detected.items():
                if available:
                    adapter = get_adapter(name, store)
                    if adapter is None:
                        continue
                    result = adapter.register_mcp(local=local)
                    if result.get("status") == "registered":
                        registered.append(name.replace("_", "-"))
            if fmt == "json":
                output({"registered": registered}, fmt="json")
            elif registered:
                success(f"MCP server registered for: {', '.join(registered)}")
            else:
                info("No supported tools detected")

    @app.command("unregister")
    def unregister_cmd(
        tool: Optional[str] = typer.Argument(
            None,
            help="Tool name (all detected if omitted). Options: claude-code, opencode, codex, gemini, cursor",
        ),
        fmt: Optional[str] = FORMAT_OPTION,
    ) -> None:
        """Remove context-teleport MCP server registration. Unregisters from all detected tools if none specified."""
        store = get_store()
        from ctx.adapters.registry import detect_adapters, get_adapter

        if tool is not None:
            adapter_key = _TOOL_MAP.get(tool, tool.replace("-", "_"))
            adapter = get_adapter(adapter_key, store)
            if adapter is None:
                error(f"Unknown tool: {tool}")
                raise typer.Exit(1)
            result = adapter.unregister_mcp()
            if fmt == "json":
                output(result, fmt="json")
            elif result["status"] == "unregistered":
                success(f"MCP server unregistered from {tool}")
            else:
                info(f"MCP server was not registered for {tool}")
        else:
            detected = detect_adapters(store)
            unregistered = []
            for name, available in detected.items():
                if available:
                    adapter = get_adapter(name, store)
                    if adapter is None:
                        continue
                    result = adapter.unregister_mcp()
                    if result.get("status") == "unregistered":
                        unregistered.append(name.replace("_", "-"))
            if fmt == "json":
                output({"unregistered": unregistered}, fmt="json")
            elif unregistered:
                success(f"MCP server unregistered from: {', '.join(unregistered)}")
            else:
                info("No registrations found to remove")


# -- Import commands (under `context-teleport import`) --


@adapter_app.command("claude-code")
def import_claude_code(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Extract from Claude Code internals into store."""
    _import_adapter("claude_code", "Claude Code", dry_run, fmt)


@adapter_app.command("opencode")
def import_opencode(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import from OpenCode (AGENTS.md, sessions) into store."""
    _import_adapter("opencode", "OpenCode", dry_run, fmt)


@adapter_app.command("codex")
def import_codex(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import from Codex (AGENTS.md, instructions) into store."""
    _import_adapter("codex", "Codex", dry_run, fmt)


@adapter_app.command("gemini")
def import_gemini(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import from Gemini (.gemini/rules, STYLEGUIDE.md) into store."""
    _import_adapter("gemini", "Gemini", dry_run, fmt)


@adapter_app.command("cursor")
def import_cursor(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import from Cursor (.cursor/rules, .cursorrules) into store."""
    _import_adapter("cursor", "Cursor", dry_run, fmt)


@adapter_app.command("bundle")
def import_bundle(
    path: str = typer.Argument(..., help="Path to .ctxbundle archive"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import a portable context bundle archive."""
    store = get_store()
    from ctx.adapters.bundle import import_bundle as do_import

    try:
        result = do_import(store, Path(path), dry_run=dry_run)
    except FileNotFoundError:
        error(f"Bundle not found: {path}")
        raise typer.Exit(1)
    except ValueError as e:
        error(f"Invalid bundle: {e}")
        raise typer.Exit(1)
    except Exception as e:
        error(f"Import failed: {e}")
        raise typer.Exit(1)
    if fmt == "json":
        output(result, fmt="json")
    elif dry_run:
        info("Dry run -- the following would be imported:")
        for item in result.get("items", []):
            info(f"  {item.get('type', 'item')}: {item.get('key', '?')} ({item.get('source', '?')})")
    else:
        success(f"Imported bundle from {path}: {result.get('imported', 0)} items")


@adapter_app.command("eda")
def import_eda(
    path: str = typer.Argument(..., help="Path to EDA artifact (file or directory)"),
    importer_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Force importer type (librelane-config, librelane-metrics, magic-drc, netgen-lvs, orfs-config, liberty)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import knowledge from EDA artifacts (configs, reports, Liberty files)."""
    from ctx.eda.parsers import auto_detect_importer, get_importer, list_importers
    from ctx.utils.paths import get_author

    target = Path(path)
    if not target.exists():
        error(f"Path not found: {path}")
        raise typer.Exit(1)

    # Resolve importer
    if importer_type:
        importer = get_importer(importer_type)
        if importer is None:
            error(f"Unknown importer type: {importer_type}")
            info(f"Available: {', '.join(list_importers())}")
            raise typer.Exit(1)
        if not importer.can_parse(target):
            error(f"Importer '{importer_type}' cannot parse: {path}")
            raise typer.Exit(1)
    else:
        importer = auto_detect_importer(target)
        if importer is None:
            error(f"No importer recognized: {path}")
            info(f"Try --type with one of: {', '.join(list_importers())}")
            raise typer.Exit(1)

    # Parse
    items = importer.parse(target)
    if not items:
        info(f"No items extracted by {importer.name}")
        if fmt == "json":
            output({"items": [], "imported": 0, "dry_run": dry_run}, fmt="json")
        return

    if dry_run:
        if fmt == "json":
            output(
                {
                    "items": [{"type": i.type, "key": i.key, "source": i.source} for i in items],
                    "imported": 0,
                    "dry_run": True,
                    "importer": importer.name,
                },
                fmt="json",
            )
        else:
            info(f"Dry run ({importer.name}) -- the following would be imported:")
            for item in items:
                info(f"  {item.type}: {item.key} ({item.source})")
        return

    # Write to store
    store = get_store()
    author = f"import:eda-{importer.name} ({get_author()})"
    imported = 0
    for item in items:
        store.set_knowledge(item.key, item.content, author=author)
        imported += 1

    if fmt == "json":
        output(
            {
                "items": [{"type": i.type, "key": i.key, "source": i.source} for i in items],
                "imported": imported,
                "dry_run": False,
                "importer": importer.name,
            },
            fmt="json",
        )
    else:
        success(f"Imported {imported} item(s) via {importer.name}")
        for item in items:
            info(f"  {item.key} <- {item.source}")


@adapter_app.command("conventions")
def import_conventions(
    path: str = typer.Argument(..., help="Path to markdown file with conventions"),
    scope: Optional[str] = typer.Option(
        None,
        "--scope",
        "-s",
        help="Scope for imported conventions (public/private/ephemeral)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import team conventions from a markdown file (split by ## headers)."""
    from ctx.core.scope import Scope

    target = Path(path)
    if not target.is_file():
        error(f"File not found: {path}")
        raise typer.Exit(1)

    text = target.read_text()
    sections = _split_conventions_file(text)

    if not sections:
        info("No conventions found in file")
        if fmt == "json":
            output({"items": [], "imported": 0, "dry_run": dry_run}, fmt="json")
        return

    if dry_run:
        if fmt == "json":
            output(
                {
                    "items": [{"key": k, "source": str(path)} for k, _ in sections],
                    "imported": 0,
                    "dry_run": True,
                },
                fmt="json",
            )
        else:
            info("Dry run -- the following conventions would be imported:")
            for key, content in sections:
                info(f"  {key} ({len(content)} chars)")
        return

    # Parse scope
    scope_val: Scope | None = None
    if scope:
        try:
            scope_val = Scope(scope.lower())
        except ValueError:
            error(f"Invalid scope '{scope}'. Use public, private, or ephemeral.")
            raise typer.Exit(1)

    from ctx.utils.paths import get_author

    store = get_store()
    author = f"import:conventions ({get_author()})"
    imported = 0
    for key, content in sections:
        store.set_convention(key, content, author=author, scope=scope_val)
        imported += 1

    if fmt == "json":
        output(
            {
                "items": [{"key": k, "source": str(path)} for k, _ in sections],
                "imported": imported,
                "dry_run": False,
            },
            fmt="json",
        )
    else:
        success(f"Imported {imported} convention(s) from {path}")
        for key, _ in sections:
            info(f"  {key}")


def _slugify_header(text: str) -> str:
    """Convert a header to a convention key."""
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"


def _split_conventions_file(text: str) -> list[tuple[str, str]]:
    """Split a markdown file into convention entries by headers.

    Strategy:
    1. Try ## headers first (each becomes a convention)
    2. If no ## headers, try # headers (skip first if it looks like a title)
    3. If no headers at all, store as single 'conventions' entry
    """
    import re

    sections: list[tuple[str, str]] = []

    # Try ## headers
    current_key = ""
    current_lines: list[str] = []
    for line in text.split("\n"):
        match = re.match(r"^##\s+(.+)", line)
        if match:
            if current_key and current_lines:
                sections.append((current_key, "\n".join(current_lines).strip()))
            current_key = _slugify_header(match.group(1))
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_key and current_lines:
        sections.append((current_key, "\n".join(current_lines).strip()))

    if sections:
        return sections

    # Try # headers (skip first if it's a document title)
    current_key = ""
    current_lines = []
    first_header = True
    for line in text.split("\n"):
        match = re.match(r"^#\s+(.+)", line)
        if match:
            if first_header:
                # Skip title header, but save any accumulated preamble
                first_header = False
                current_lines = []
                continue
            if current_key and current_lines:
                sections.append((current_key, "\n".join(current_lines).strip()))
            current_key = _slugify_header(match.group(1))
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_key and current_lines:
        sections.append((current_key, "\n".join(current_lines).strip()))

    if sections:
        return sections

    # No headers at all -- single entry
    if text.strip():
        return [("conventions", text.strip())]

    return []


@adapter_app.command("github")
def import_github(
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "-r",
        help="GitHub repository (owner/repo). Auto-detected from git remote if omitted.",
    ),
    labels: Optional[str] = typer.Option(
        None,
        "--labels",
        "-l",
        help="Comma-separated labels to filter by",
    ),
    state: str = typer.Option(
        "all",
        "--state",
        "-s",
        help="Issue state: open, closed, all",
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Only issues created after this date (ISO format, e.g. 2025-01-01)",
    ),
    issue_number: Optional[int] = typer.Option(
        None,
        "--issue",
        "-i",
        help="Import a single issue by number",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of issues to fetch",
    ),
    as_decisions: bool = typer.Option(
        False,
        "--as-decisions",
        help="Also create decision records for closed issues",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import knowledge from GitHub issues via gh CLI."""
    from ctx.sources.github import GitHubSource, GitHubSourceError

    source = GitHubSource()

    # Resolve repo
    resolved_repo = repo
    if resolved_repo is None:
        resolved_repo = source.detect_repo()
        if resolved_repo is None:
            error("Cannot detect GitHub repository. Use --repo owner/repo")
            raise typer.Exit(1)
        info(f"Auto-detected repository: {resolved_repo}")

    from ctx.sources.base import SourceConfig

    config = SourceConfig(
        repo=resolved_repo,
        labels=[lb.strip() for lb in labels.split(",") if lb.strip()] if labels else [],
        state=state,
        since=since or "",
        issue_number=issue_number,
        limit=limit,
        as_decisions=as_decisions,
    )

    try:
        items = source.import_issues(config)
    except GitHubSourceError as e:
        error(str(e))
        raise typer.Exit(1)

    if not items:
        if fmt == "json":
            output({"items": [], "imported": 0, "dry_run": dry_run}, fmt="json")
        else:
            info("No issues found matching the criteria")
        return

    if dry_run:
        if fmt == "json":
            output(
                {
                    "items": [
                        {"type": it.type, "key": it.key, "source": it.source}
                        for it in items
                    ],
                    "imported": 0,
                    "dry_run": True,
                },
                fmt="json",
            )
        else:
            info("Dry run -- the following would be imported:")
            for it in items:
                info(f"  {it.type}: {it.key} ({it.source})")
        return

    # Write to store
    from ctx.utils.paths import get_author

    store = get_store()
    author = f"import:github ({get_author()})"
    imported_knowledge = 0
    imported_decisions = 0

    for it in items:
        if it.type == "knowledge":
            store.set_knowledge(it.key, it.content, author=author)
            imported_knowledge += 1
        elif it.type == "decision":
            store.add_decision(
                title=it.title,
                context=it.context,
                decision_text=it.decision_text,
                consequences=it.consequences,
                author=author,
            )
            imported_decisions += 1

    total = imported_knowledge + imported_decisions
    if fmt == "json":
        output(
            {
                "items": [
                    {"type": it.type, "key": it.key, "source": it.source}
                    for it in items
                ],
                "imported": total,
                "knowledge": imported_knowledge,
                "decisions": imported_decisions,
                "dry_run": False,
            },
            fmt="json",
        )
    else:
        parts = []
        if imported_knowledge:
            parts.append(f"{imported_knowledge} knowledge")
        if imported_decisions:
            parts.append(f"{imported_decisions} decision(s)")
        success(f"Imported {' + '.join(parts)} from GitHub issues")
        for it in items:
            info(f"  {it.type}: {it.key}")


# -- Export commands (under `context-teleport export`) --


@export_app.command("claude-code")
def export_claude_code(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be exported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Inject store content into Claude Code locations."""
    _export_adapter("claude_code", "Claude Code", dry_run, fmt)


@export_app.command("opencode")
def export_opencode(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be exported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Export store content to OpenCode (AGENTS.md)."""
    _export_adapter("opencode", "OpenCode", dry_run, fmt)


@export_app.command("codex")
def export_codex(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be exported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Export store content to Codex (AGENTS.md)."""
    _export_adapter("codex", "Codex", dry_run, fmt)


@export_app.command("gemini")
def export_gemini(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be exported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Export store content to Gemini (.gemini/rules)."""
    _export_adapter("gemini", "Gemini", dry_run, fmt)


@export_app.command("cursor")
def export_cursor(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be exported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Export store content to Cursor (.cursor/rules)."""
    _export_adapter("cursor", "Cursor", dry_run, fmt)


@export_app.command("bundle")
def export_bundle(
    path: str = typer.Argument(..., help="Output path for .ctxbundle archive"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be exported"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Export store as a portable .ctxbundle archive."""
    store = get_store()
    from ctx.adapters.bundle import export_bundle as do_export

    try:
        result = do_export(store, Path(path), dry_run=dry_run)
    except FileNotFoundError:
        error(f"Path not found: {path}")
        raise typer.Exit(1)
    except PermissionError:
        error(f"Permission denied: {path}")
        raise typer.Exit(1)
    except Exception as e:
        error(f"Export failed: {e}")
        raise typer.Exit(1)
    if fmt == "json":
        output(result, fmt="json")
    elif dry_run:
        info("Dry run -- the following would be bundled:")
        for item in result.get("items", []):
            info(f"  {item.get('target', '?')}")
    else:
        success(f"Bundle exported to {path}")
