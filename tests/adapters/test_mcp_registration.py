"""Tests for MCP server registration/unregistration in .claude/mcp.json."""

from __future__ import annotations

import json

import pytest

from ctx.adapters.claude_code import ClaudeCodeAdapter
from ctx.adapters.cursor import CursorAdapter
from ctx.adapters.gemini import GeminiAdapter
from ctx.adapters.opencode import OpenCodeAdapter
from ctx.core.store import ContextStore


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="test-registration")
    return s


class TestRegisterMCP:
    def test_register_creates_config(self, store):
        adapter = ClaudeCodeAdapter(store)
        result = adapter.register_mcp_server()

        assert result["status"] == "registered"
        config_path = store.root / ".claude" / "mcp.json"
        assert config_path.is_file()

        config = json.loads(config_path.read_text())
        assert "context-teleport" in config["mcpServers"]
        entry = config["mcpServers"]["context-teleport"]
        assert entry["command"] == "uvx"
        assert entry["args"] == ["context-teleport"]

    def test_register_local_mode(self, store):
        adapter = ClaudeCodeAdapter(store)
        result = adapter.register_mcp_server(local=True)

        assert result["status"] == "registered"
        config_path = store.root / ".claude" / "mcp.json"
        config = json.loads(config_path.read_text())
        entry = config["mcpServers"]["context-teleport"]
        assert entry["command"] == "ctx-mcp"
        assert "args" not in entry

    def test_register_is_idempotent(self, store):
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp_server()
        adapter.register_mcp_server()

        config_path = store.root / ".claude" / "mcp.json"
        config = json.loads(config_path.read_text())
        # Should still have exactly one entry
        assert len(config["mcpServers"]) == 1

    def test_register_preserves_existing_servers(self, store):
        config_path = store.root / ".claude" / "mcp.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({
            "mcpServers": {
                "other-server": {"command": "other-cmd"}
            }
        }))

        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp_server()

        config = json.loads(config_path.read_text())
        assert "other-server" in config["mcpServers"]
        assert "context-teleport" in config["mcpServers"]

    def test_unregister_removes_server(self, store):
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp_server()
        result = adapter.unregister_mcp_server()

        assert result["status"] == "unregistered"
        config_path = store.root / ".claude" / "mcp.json"
        config = json.loads(config_path.read_text())
        assert "context-teleport" not in config["mcpServers"]

    def test_unregister_when_not_registered(self, store):
        adapter = ClaudeCodeAdapter(store)
        result = adapter.unregister_mcp_server()
        assert result["status"] == "not_registered"

    def test_register_handles_corrupt_json(self, store):
        config_path = store.root / ".claude" / "mcp.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("not valid json{{{")

        adapter = ClaudeCodeAdapter(store)
        result = adapter.register_mcp_server()

        assert result["status"] == "registered"
        config = json.loads(config_path.read_text())
        assert "context-teleport" in config["mcpServers"]


class TestRegisterMCPEnv:
    """Verify MCP_CALLER env and uvx args are set correctly in each adapter's registration."""

    def test_claude_code_sets_env(self, store):
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp_server()

        config_path = store.root / ".claude" / "mcp.json"
        config = json.loads(config_path.read_text())
        entry = config["mcpServers"]["context-teleport"]
        assert entry["command"] == "uvx"
        assert entry["args"] == ["context-teleport"]
        assert entry["env"] == {"MCP_CALLER": "mcp:claude-code"}

    def test_opencode_sets_env(self, store):
        adapter = OpenCodeAdapter(store)
        adapter.register_mcp()

        config_path = store.root / "opencode.json"
        config = json.loads(config_path.read_text())
        entry = config["mcpServers"]["context-teleport"]
        assert entry["command"] == "uvx"
        assert entry["args"] == ["context-teleport"]
        assert entry["env"] == {"MCP_CALLER": "mcp:opencode"}

    def test_cursor_sets_env(self, store):
        adapter = CursorAdapter(store)
        adapter.register_mcp()

        config_path = store.root / ".cursor" / "mcp.json"
        config = json.loads(config_path.read_text())
        entry = config["mcpServers"]["context-teleport"]
        assert entry["command"] == "uvx"
        assert entry["args"] == ["context-teleport"]
        assert entry["env"] == {"MCP_CALLER": "mcp:cursor"}

    def test_gemini_sets_env(self, store):
        adapter = GeminiAdapter(store)
        adapter.register_mcp()

        config_path = store.root / ".gemini" / "settings.json"
        config = json.loads(config_path.read_text())
        entry = config["mcpServers"]["context-teleport"]
        assert entry["command"] == "uvx"
        assert entry["args"] == ["context-teleport"]
        assert entry["env"] == {"MCP_CALLER": "mcp:gemini"}
