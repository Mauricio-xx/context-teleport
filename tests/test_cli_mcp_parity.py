"""CLI / MCP parity tests: verify both interfaces produce identical store side-effects."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import git
import pytest
from typer.testing import CliRunner

from ctx.cli.main import app
from ctx.core.store import ContextStore
from ctx.mcp.server import set_store

runner = CliRunner()

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SERVER_PY = _PROJECT_ROOT / "src" / "ctx" / "mcp" / "server.py"


@pytest.fixture
def cli_store(tmp_path):
    """Create a git repo, chdir into it, and init a context store."""
    cli_root = tmp_path / "cli"
    cli_root.mkdir()
    repo = git.Repo.init(cli_root)
    readme = cli_root / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    original = os.getcwd()
    os.chdir(cli_root)
    result = runner.invoke(app, ["init", "--name", "parity-test"])
    assert result.exit_code == 0
    yield cli_root
    os.chdir(original)


@pytest.fixture
def mcp_store(tmp_path):
    """Create a git repo with initialized store and inject it for MCP functions."""
    mcp_root = tmp_path / "mcp"
    mcp_root.mkdir()
    repo = git.Repo.init(mcp_root)
    readme = mcp_root / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    store = ContextStore(mcp_root)
    store.init(project_name="parity-test")
    set_store(store)
    yield store


class TestSideEffectParity:
    """Both CLI and MCP should produce the same store entries."""

    def test_knowledge_add_parity(self, cli_store, mcp_store):
        """CLI knowledge set and MCP context_add_knowledge produce the same entry."""
        # CLI
        runner.invoke(app, ["knowledge", "set", "arch", "Hexagonal architecture"])
        cli_entry = ContextStore(cli_store).get_knowledge("arch")

        # MCP
        from ctx.mcp.server import context_add_knowledge

        context_add_knowledge(key="arch", content="Hexagonal architecture")
        mcp_entry = mcp_store.get_knowledge("arch")

        assert cli_entry is not None
        assert mcp_entry is not None
        assert cli_entry.content == mcp_entry.content
        assert cli_entry.key == mcp_entry.key

    def test_convention_add_parity(self, cli_store, mcp_store):
        """CLI convention add and MCP context_add_convention produce the same entry."""
        runner.invoke(app, ["convention", "add", "git"], input="Always rebase before merge")
        cli_entry = ContextStore(cli_store).get_convention("git")

        from ctx.mcp.server import context_add_convention

        context_add_convention(key="git", content="Always rebase before merge")
        mcp_entry = mcp_store.get_convention("git")

        assert cli_entry is not None
        assert mcp_entry is not None
        assert cli_entry.content == mcp_entry.content
        assert cli_entry.key == mcp_entry.key

    def test_activity_check_in_parity(self, cli_store, mcp_store):
        """CLI check-in and MCP context_check_in produce equivalent activity entries."""
        runner.invoke(app, ["activity", "check-in", "testing parity"])
        cli_entries = ContextStore(cli_store).list_activity()
        cli_tasks = [e.task for e in cli_entries]

        from ctx.mcp.server import context_check_in

        context_check_in(task="testing parity")
        mcp_entries = mcp_store.list_activity()
        mcp_tasks = [e.task for e in mcp_entries]

        assert "testing parity" in cli_tasks
        assert "testing parity" in mcp_tasks

    def test_activity_check_out_parity(self, cli_store, mcp_store):
        """Both CLI and MCP check-out remove the activity entry."""
        # Set up activity first
        runner.invoke(app, ["activity", "check-in", "will check out"])
        runner.invoke(app, ["activity", "check-out"])
        cli_entries = ContextStore(cli_store).list_activity()

        from ctx.mcp.server import context_check_in, context_check_out

        context_check_in(task="will check out")
        context_check_out()
        mcp_entries = mcp_store.list_activity()

        assert len(cli_entries) == 0
        assert len(mcp_entries) == 0

    def test_sync_push_parity(self, cli_store, mcp_store):
        """Both CLI and MCP push create a git commit in the local repo."""
        # CLI: add content then push
        runner.invoke(app, ["knowledge", "set", "push-test", "data"])
        runner.invoke(app, ["sync", "push"])
        cli_repo = git.Repo(cli_store)
        cli_msgs = [c.message for c in cli_repo.iter_commits(max_count=3)]
        assert any(".context-teleport" in m or "ctx" in m.lower() for m in cli_msgs)

        # MCP: add content then push
        from ctx.mcp.server import context_add_knowledge, context_sync_push

        context_add_knowledge(key="push-test", content="data")
        result_json = context_sync_push()
        result = json.loads(result_json)
        assert result["status"] == "committed"


class TestStatusConventions:
    """Verify MCP tools follow consistent status return conventions."""

    def _get_write_tool_functions(self) -> list[str]:
        """Extract names of MCP tool functions that return status 'ok'."""
        source = _SERVER_PY.read_text()
        # Find all tool functions that return {"status": "ok", ...}
        return re.findall(r'def (context_\w+)\(.*?\).*?return json\.dumps\(\{"status": "ok"', source, re.DOTALL)

    def test_mcp_write_tools_return_ok(self):
        """All MCP write tools should return status='ok' on the success path."""
        source = _SERVER_PY.read_text()
        # Find tool function blocks and check they use "ok" for success writes
        write_tools = [
            "context_add_knowledge",
            "context_add_convention",
            "context_add_skill",
            "context_check_in",
            "context_record_decision",
            "context_update_state",
            "context_append_session",
            "context_report_skill_usage",
            "context_rate_skill",
            "context_propose_skill_improvement",
            "context_set_scope",
            "context_set",
        ]
        for tool in write_tools:
            # Each write tool should have a "status": "ok" return
            pattern = rf'def {tool}\(.*?\n(?:.*?\n)*?.*?"status":\s*"ok"'
            assert re.search(pattern, source), (
                f"Write tool {tool} does not return status='ok' on success path"
            )

    def test_mcp_remove_tools_return_removed(self):
        """All MCP remove tools should return status='removed' on success."""
        source = _SERVER_PY.read_text()
        remove_tools = [
            "context_remove_knowledge",
            "context_rm_convention",
            "context_remove_skill",
        ]
        for tool in remove_tools:
            pattern = rf'def {tool}\(.*?\n(?:.*?\n)*?.*?"status":\s*"removed"'
            assert re.search(pattern, source), (
                f"Remove tool {tool} does not return status='removed' on success path"
            )
