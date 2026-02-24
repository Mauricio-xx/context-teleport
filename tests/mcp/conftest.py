"""E2E fixtures: spawn ctx-mcp subprocess and connect via MCP protocol."""

from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import git
import pytest

from ctx.core.store import ContextStore
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

_SRC_DIR = str(Path(__file__).resolve().parents[2] / "src")


@asynccontextmanager
async def spawn_mcp_session(cwd: Path, extra_env: dict | None = None):
    """Spawn ctx-mcp as a subprocess and yield an initialized ClientSession."""
    env = {**os.environ, "PYTHONPATH": _SRC_DIR}
    if extra_env:
        env.update(extra_env)
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ctx.mcp.server"],
        cwd=str(cwd),
        env=env,
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


@asynccontextmanager
async def spawn_mcp_from_config(cwd: Path, config_path: Path):
    """Read an MCP JSON config, extract the server entry, and spawn from it.

    This simulates what a real tool (Claude Code, Cursor, etc.) does:
    read its mcp.json, find the server entry, and spawn the process.
    """
    config = json.loads(config_path.read_text())
    entry = config["mcpServers"]["context-teleport"]

    # Merge env from config into process env
    env = {**os.environ, "PYTHONPATH": _SRC_DIR}
    if "env" in entry:
        env.update(entry["env"])

    # Use sys.executable -m ctx.mcp.server instead of the entry command
    # (the entry uses ctx-mcp which may not be on PATH during tests)
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ctx.mcp.server"],
        cwd=str(cwd),
        env=env,
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


@pytest.fixture
def e2e_store(tmp_path: Path) -> Path:
    """Create a temp git repo with an initialized context store. Returns the path."""
    repo = git.Repo.init(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# E2E Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")

    store = ContextStore(tmp_path)
    store.init(project_name="e2e-test-project")
    return tmp_path


@pytest.fixture
def populated_e2e_store(e2e_store: Path) -> Path:
    """E2E store pre-filled with knowledge and decisions."""
    store = ContextStore(e2e_store)
    store.set_knowledge("architecture", "Hexagonal architecture with ports and adapters")
    store.set_knowledge("conventions", "Python 3.11+, ruff linter, pytest for tests")
    store.add_decision(
        title="Use PostgreSQL",
        context="Need a production database",
        decision_text="PostgreSQL over SQLite",
        consequences="Requires managed DB",
    )
    return e2e_store
