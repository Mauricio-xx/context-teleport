"""Shared MCP registration helpers for JSON and YAML config files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SERVER_NAME = "context-teleport"


def _server_entry(caller_name: str = "", local: bool = False) -> dict:
    """Build the MCP server entry dict, optionally setting MCP_CALLER env.

    When local=False (default), uses ``uvx --from context-teleport python -m
    ctx.mcp.server`` so the MCP server is launched directly, bypassing the
    TTY-based CLI/MCP dispatch in the entry point.
    When local=True, uses ``python -m ctx.mcp.server`` (requires PATH/venv).
    """
    if local:
        entry: dict = {
            "command": "python",
            "args": ["-m", "ctx.mcp.server"],
            "type": "stdio",
        }
    else:
        entry = {
            "command": "uvx",
            "args": ["--from", "context-teleport", "python", "-m", "ctx.mcp.server"],
            "type": "stdio",
        }
    if caller_name:
        entry["env"] = {"MCP_CALLER": caller_name}
    return entry


def _safe_read_json(path: Path) -> dict:
    """Read a JSON file, returning empty dict on any error."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse MCP config %s: %s", path, exc)
        return {}


def register_mcp_json(
    config_path: Path,
    server_name: str = SERVER_NAME,
    caller_name: str = "",
    local: bool = False,
) -> dict:
    """Register context-teleport in a JSON config file with mcpServers key.

    Works for Claude (.claude/mcp.json), Cursor (.cursor/mcp.json),
    OpenCode (opencode.json), etc.
    Creates the file if it doesn't exist. Idempotent.
    """
    config = _safe_read_json(config_path)
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    config["mcpServers"][server_name] = _server_entry(caller_name, local=local)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return {
        "status": "registered",
        "path": str(config_path),
        "server": server_name,
    }


def unregister_mcp_json(config_path: Path, server_name: str = SERVER_NAME) -> dict:
    """Remove context-teleport from a JSON config file."""
    config = _safe_read_json(config_path)
    servers = config.get("mcpServers", {})
    if server_name not in servers:
        return {"status": "not_registered"}
    del servers[server_name]
    config["mcpServers"] = servers
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return {
        "status": "unregistered",
        "path": str(config_path),
    }


# ---------------------------------------------------------------------------
# OpenCode-specific helpers (different JSON schema from Claude/Cursor)
# ---------------------------------------------------------------------------

def _opencode_server_entry(caller_name: str = "", local: bool = False) -> dict:
    """Build an MCP server entry in OpenCode's config format.

    OpenCode uses a different schema:
    - ``command`` is an array (not a string with separate ``args``)
    - ``type`` is ``"local"`` (not ``"stdio"``)
    - Environment key is ``"environment"`` (not ``"env"``)
    - Schema is strict (no extra fields allowed)
    """
    if local:
        entry: dict = {
            "type": "local",
            "command": ["python", "-m", "ctx.mcp.server"],
        }
    else:
        entry = {
            "type": "local",
            "command": ["uvx", "--from", "context-teleport", "python", "-m", "ctx.mcp.server"],
        }
    if caller_name:
        entry["environment"] = {"MCP_CALLER": caller_name}
    return entry


def register_mcp_opencode(
    config_path: Path,
    server_name: str = SERVER_NAME,
    caller_name: str = "",
    local: bool = False,
) -> dict:
    """Register context-teleport in OpenCode's config format.

    OpenCode uses ``{"mcp": {"server-name": {...}}}`` with ``command`` as an
    array and ``type: "local"``, unlike Claude/Cursor's ``mcpServers`` format.
    """
    config = _safe_read_json(config_path)
    if "mcp" not in config:
        config["mcp"] = {}
    config["mcp"][server_name] = _opencode_server_entry(caller_name, local=local)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return {
        "status": "registered",
        "path": str(config_path),
        "server": server_name,
    }


def unregister_mcp_opencode(
    config_path: Path, server_name: str = SERVER_NAME
) -> dict:
    """Remove context-teleport from an OpenCode config file."""
    config = _safe_read_json(config_path)
    servers = config.get("mcp", {})
    if server_name not in servers:
        return {"status": "not_registered"}
    del servers[server_name]
    config["mcp"] = servers
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return {
        "status": "unregistered",
        "path": str(config_path),
    }
