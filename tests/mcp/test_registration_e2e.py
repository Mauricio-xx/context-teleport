"""E2E tests: register adapter, spawn MCP server from config, verify full chain."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctx.adapters.claude_code import ClaudeCodeAdapter
from ctx.adapters.cursor import CursorAdapter
from ctx.adapters.opencode import OpenCodeAdapter
from ctx.core.store import ContextStore
from tests.mcp.conftest import spawn_mcp_from_config

pytestmark = pytest.mark.anyio


class TestClaudeCodeRegistrationE2E:
    """Full register -> spawn -> call chain for Claude Code adapter."""

    async def test_register_then_spawn(self, e2e_store):
        store = ContextStore(e2e_store)
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp_server()

        config_path = store.root / ".claude" / "mcp.json"
        async with spawn_mcp_from_config(e2e_store, config_path) as session:
            result = await session.list_tools()
            assert len(result.tools) == 29

    async def test_register_sets_env(self, e2e_store):
        store = ContextStore(e2e_store)
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp_server()

        config_path = store.root / ".claude" / "mcp.json"
        config = json.loads(config_path.read_text())
        entry = config["mcpServers"]["context-teleport"]
        assert entry["env"]["MCP_CALLER"] == "mcp:claude-code"

    async def test_register_spawn_add_knowledge(self, e2e_store):
        """Full round-trip: register, spawn, add knowledge via MCP, verify attribution."""
        store = ContextStore(e2e_store)
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp_server()

        config_path = store.root / ".claude" / "mcp.json"
        async with spawn_mcp_from_config(e2e_store, config_path) as session:
            result = await session.call_tool(
                "context_add_knowledge",
                {"key": "e2e-roundtrip", "content": "Added via registered MCP"},
            )
            data = json.loads(result.content[0].text)
            assert data["status"] == "ok"

        # Verify agent attribution on disk
        reloaded = ContextStore(e2e_store)
        entry = reloaded.get_knowledge("e2e-roundtrip")
        assert entry is not None
        assert entry.author == "mcp:claude-code"

    async def test_instructions_contain_project_name(self, e2e_store):
        """After register + spawn, the server instructions include the project name."""
        store = ContextStore(e2e_store)
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp_server()

        config_path = store.root / ".claude" / "mcp.json"
        config = json.loads(config_path.read_text())
        entry = config["mcpServers"]["context-teleport"]

        import os
        import sys
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        src_dir = str(Path(__file__).resolve().parents[2] / "src")
        env = {**os.environ, "PYTHONPATH": src_dir}
        if "env" in entry:
            env.update(entry["env"])

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "ctx.mcp.server"],
            cwd=str(e2e_store),
            env=env,
        )
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                init_result = await session.initialize()
                assert init_result.instructions is not None
                assert "e2e-test-project" in init_result.instructions


class TestCursorRegistrationE2E:
    """Full register -> spawn -> call chain for Cursor adapter."""

    async def test_register_then_spawn(self, e2e_store):
        store = ContextStore(e2e_store)
        adapter = CursorAdapter(store)
        adapter.register_mcp()

        config_path = store.root / ".cursor" / "mcp.json"
        async with spawn_mcp_from_config(e2e_store, config_path) as session:
            result = await session.list_tools()
            assert len(result.tools) == 29


class TestOpenCodeRegistrationE2E:
    """Full register -> spawn -> call chain for OpenCode adapter."""

    async def test_register_then_spawn(self, e2e_store):
        store = ContextStore(e2e_store)
        adapter = OpenCodeAdapter(store)
        adapter.register_mcp()

        config_path = store.root / "opencode.json"
        async with spawn_mcp_from_config(e2e_store, config_path) as session:
            result = await session.list_tools()
            assert len(result.tools) == 29
