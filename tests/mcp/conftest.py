"""E2E fixtures: spawn ctx-mcp subprocess and connect via MCP protocol."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import git
import pytest

from ctx.core.store import ContextStore
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@asynccontextmanager
async def spawn_mcp_session(cwd: Path):
    """Spawn ctx-mcp as a subprocess and yield an initialized ClientSession."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ctx.mcp.server"],
        cwd=str(cwd),
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
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
