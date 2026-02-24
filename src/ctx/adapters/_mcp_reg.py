"""Shared MCP registration helpers for JSON and YAML config files."""

from __future__ import annotations

import json
from pathlib import Path

SERVER_NAME = "context-teleport"


def _server_entry(caller_name: str = "", local: bool = False) -> dict:
    """Build the MCP server entry dict, optionally setting MCP_CALLER env.

    When local=False (default), uses ``uvx context-teleport`` so the package
    is resolved automatically without needing an activated venv.
    When local=True, uses ``ctx-mcp`` directly (requires PATH/venv).
    """
    if local:
        entry: dict = {
            "command": "ctx-mcp",
            "type": "stdio",
        }
    else:
        entry = {
            "command": "uvx",
            "args": ["context-teleport"],
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
    except (json.JSONDecodeError, OSError):
        return {}


def register_mcp_json(
    config_path: Path,
    server_name: str = SERVER_NAME,
    caller_name: str = "",
    local: bool = False,
) -> dict:
    """Register ctx-mcp in a JSON config file with mcpServers key.

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
    """Remove ctx-mcp from a JSON config file."""
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
