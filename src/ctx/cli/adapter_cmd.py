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
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Import a portable context bundle archive."""
    store = get_store()
    from ctx.adapters.bundle import import_bundle as do_import

    try:
        result = do_import(store, Path(path))
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
    else:
        success(f"Imported bundle from {path}: {result.get('imported', 0)} items")


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
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Export store as a portable .ctxbundle archive."""
    store = get_store()
    from ctx.adapters.bundle import export_bundle as do_export

    try:
        result = do_export(store, Path(path))
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
    else:
        success(f"Bundle exported to {path}")
