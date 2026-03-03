"""Tests for OpenCode adapter."""

import json
from pathlib import Path

from ctx.adapters.opencode import OpenCodeAdapter
from ctx.utils.paths import opencode_data_dir


class TestDetect:
    def test_detect_with_directory(self, store):
        (store.root / ".opencode").mkdir()
        adapter = OpenCodeAdapter(store)
        assert adapter.detect() is True

    def test_detect_with_config(self, store):
        (store.root / "opencode.json").write_text("{}")
        adapter = OpenCodeAdapter(store)
        assert adapter.detect() is True

    def test_detect_neither(self, store, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        adapter = OpenCodeAdapter(store)
        assert adapter.detect() is False


class TestImport:
    def test_import_agents_md(self, store):
        agents = store.root / "AGENTS.md"
        agents.write_text("## Architecture\nHexagonal pattern\n\n## Stack\nPython\n")
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 2
        entry = store.get_knowledge("architecture")
        assert entry is not None
        assert "Hexagonal" in entry.content

    def test_import_dry_run(self, store):
        agents = store.root / "AGENTS.md"
        agents.write_text("## Test\nContent\n")
        # Also add an agent definition so we test all sources in dry_run
        agents_dir = store.root / ".opencode" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "reviewer.md").write_text("---\ndescription: Code reviewer\n---\nReview code\n")
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context(dry_run=True)
        assert result["dry_run"] is True
        assert result["imported"] == 0
        assert len(result["items"]) == 2  # AGENTS.md entry + agent def


class TestImportAgents:
    def test_import_agents_md_file(self, store):
        agents_dir = store.root / ".opencode" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "reviewer.md").write_text(
            "---\ndescription: Code reviewer\nmode: diff\n---\n\nReview all code changes.\n"
        )
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("opencode-agent-reviewer")
        assert entry is not None
        assert "Review all code changes" in entry.content

    def test_import_agents_nested(self, store):
        nested_dir = store.root / ".opencode" / "agents" / "python"
        nested_dir.mkdir(parents=True)
        (nested_dir / "linter.md").write_text("Run ruff on Python files.\n")
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("opencode-agent-python-linter")
        assert entry is not None
        assert "ruff" in entry.content

    def test_import_agent_dir_singular(self, store):
        """OpenCode also accepts .opencode/agent/ (singular)."""
        agent_dir = store.root / ".opencode" / "agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "helper.md").write_text("General helper agent.\n")
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("opencode-agent-helper")
        assert entry is not None

    def test_import_agents_no_dir(self, store):
        """No .opencode/agents/ dir should produce no items."""
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 0


class TestImportCommands:
    def test_import_commands_md(self, store):
        cmds_dir = store.root / ".opencode" / "commands"
        cmds_dir.mkdir(parents=True)
        (cmds_dir / "test.md").write_text(
            "---\ndescription: Run tests\ntemplate: pytest {{path}}\n---\n\nRun the test suite.\n"
        )
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("opencode-command-test")
        assert entry is not None
        assert "Run the test suite" in entry.content

    def test_import_command_dir_singular(self, store):
        """OpenCode also accepts .opencode/command/ (singular)."""
        cmd_dir = store.root / ".opencode" / "command"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "deploy.md").write_text("Deploy the application.\n")
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("opencode-command-deploy")
        assert entry is not None


class TestImportSessions:
    def _setup_session_dir(self, store, monkeypatch, tmp_path):
        """Create a fake OpenCode data dir with session JSON files."""
        data_dir = tmp_path / "opencode-data"
        monkeypatch.setenv("OPENCODE_DATA_DIR", str(data_dir))

        # Get the project ID (root commit hash)
        from git import Repo

        repo = Repo(store.root)
        project_id = repo.git.rev_list("HEAD", max_parents=0).strip().split("\n")[0]

        sessions_dir = data_dir / "storage" / "session" / project_id
        sessions_dir.mkdir(parents=True)
        return sessions_dir

    def test_import_sessions_from_json(self, store, monkeypatch, tmp_path):
        sessions_dir = self._setup_session_dir(store, monkeypatch, tmp_path)

        session_data = {
            "title": "Fix auth bug",
            "summary": {"additions": 42, "deletions": 10, "files": 3},
            "time": {"created": "2025-06-15T10:00:00Z", "updated": 1718440800},
        }
        (sessions_dir / "abcdef1234567890.json").write_text(json.dumps(session_data))

        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()

        session_items = [i for i in result["items"] if i["key"].startswith("opencode-session-")]
        assert len(session_items) == 1
        assert session_items[0]["key"] == "opencode-session-abcdef12"
        assert result["imported"] == 1

        entry = store.get_knowledge("opencode-session-abcdef12")
        assert entry is not None
        assert "Fix auth bug" in entry.content
        assert "+42/-10" in entry.content
        assert "3 files" in entry.content

    def test_import_sessions_limits_to_20(self, store, monkeypatch, tmp_path):
        sessions_dir = self._setup_session_dir(store, monkeypatch, tmp_path)

        for i in range(25):
            data = {
                "title": f"Session {i}",
                "summary": {"additions": i, "deletions": 0, "files": 1},
                "time": {"updated": 1000 + i},
            }
            (sessions_dir / f"session{i:04d}aabbccdd.json").write_text(json.dumps(data))

        adapter = OpenCodeAdapter(store)
        result = adapter.import_context(dry_run=True)
        session_items = [i for i in result["items"] if i["key"].startswith("opencode-session-")]
        assert len(session_items) == 20

    def test_import_sessions_no_data_dir(self, store, monkeypatch, tmp_path):
        """Gracefully skip when data dir doesn't exist."""
        monkeypatch.setenv("OPENCODE_DATA_DIR", str(tmp_path / "nonexistent"))
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        session_items = [i for i in result["items"] if i["key"].startswith("opencode-session-")]
        assert len(session_items) == 0

    def test_import_sessions_no_git(self, tmp_path):
        """Gracefully skip when not in a git repo."""
        from ctx.core.store import ContextStore

        # Create a store in a non-git directory
        store = ContextStore(tmp_path)
        store.init(project_name="no-git")
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context()
        session_items = [i for i in result["items"] if i["key"].startswith("opencode-session-")]
        assert len(session_items) == 0


class TestExport:
    def test_export_agents_md(self, store):
        store.set_knowledge("arch", "Architecture notes")
        adapter = OpenCodeAdapter(store)
        result = adapter.export_context()
        assert result["exported"] == 1
        agents = store.root / "AGENTS.md"
        assert agents.is_file()
        content = agents.read_text()
        assert "arch" in content

    def test_export_preserves_existing(self, store):
        agents = store.root / "AGENTS.md"
        agents.write_text("## Custom Rules\nMy rules here.\n")
        store.set_knowledge("arch", "Architecture")
        adapter = OpenCodeAdapter(store)
        adapter.export_context()
        content = agents.read_text()
        assert "Custom Rules" in content
        assert "arch" in content


class TestExportDecisions:
    def test_export_includes_decisions(self, store):
        store.add_decision(
            title="Use PostgreSQL",
            context="Need a production database",
            decision_text="PostgreSQL over SQLite",
        )
        store.add_decision(
            title="Use Redis for caching",
            context="Need caching layer",
            decision_text="Redis for cache",
        )
        adapter = OpenCodeAdapter(store)
        result = adapter.export_context()
        assert result["exported"] >= 1

        agents = store.root / "AGENTS.md"
        content = agents.read_text()
        assert "decisions" in content.lower()
        assert "Use PostgreSQL" in content
        assert "Use Redis" in content
        assert "0001" in content
        assert "0002" in content

    def test_export_decisions_only(self, store):
        """Decisions alone should trigger AGENTS.md export."""
        store.add_decision(title="Use Go", decision_text="Rewrite in Go")
        adapter = OpenCodeAdapter(store)
        result = adapter.export_context()
        assert result["exported"] >= 1
        agents = store.root / "AGENTS.md"
        assert agents.is_file()
        assert "Use Go" in agents.read_text()

    def test_export_decisions_with_knowledge(self, store):
        """Decisions and knowledge together in managed section."""
        store.set_knowledge("stack", "Python 3.12")
        store.add_decision(title="Use pytest", decision_text="pytest over unittest")
        adapter = OpenCodeAdapter(store)
        adapter.export_context()
        content = (store.root / "AGENTS.md").read_text()
        assert "stack" in content
        assert "Use pytest" in content

    def test_export_empty_store(self, store):
        adapter = OpenCodeAdapter(store)
        result = adapter.export_context()
        assert result["exported"] == 0
        assert not (store.root / "AGENTS.md").exists()

    def test_export_dry_run_decisions(self, store):
        store.add_decision(title="Use Kafka", decision_text="Event streaming")
        adapter = OpenCodeAdapter(store)
        result = adapter.export_context(dry_run=True)
        assert result["dry_run"] is True
        assert result["exported"] == 0
        assert len(result["items"]) >= 1
        assert "1 decisions" in result["items"][0]["description"]


class TestMcp:
    def test_register(self, store):
        adapter = OpenCodeAdapter(store)
        result = adapter.register_mcp()
        assert result["status"] == "registered"
        config = json.loads((store.root / "opencode.json").read_text())
        assert "context-teleport" in config["mcp"]
        entry = config["mcp"]["context-teleport"]
        assert entry["type"] == "local"
        assert entry["command"] == ["uvx", "--from", "context-teleport", "python", "-m", "ctx.mcp.server"]
        assert entry["environment"] == {"MCP_CALLER": "mcp:opencode"}

    def test_register_local(self, store):
        adapter = OpenCodeAdapter(store)
        result = adapter.register_mcp(local=True)
        assert result["status"] == "registered"
        config = json.loads((store.root / "opencode.json").read_text())
        entry = config["mcp"]["context-teleport"]
        assert entry["type"] == "local"
        assert entry["command"] == ["python", "-m", "ctx.mcp.server"]

    def test_unregister(self, store):
        adapter = OpenCodeAdapter(store)
        adapter.register_mcp()
        result = adapter.unregister_mcp()
        assert result["status"] == "unregistered"


class TestOpenCodeDataDir:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("OPENCODE_DATA_DIR", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        result = opencode_data_dir()
        assert result == Path.home() / ".local" / "share" / "opencode"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_DATA_DIR", "/custom/opencode")
        result = opencode_data_dir()
        assert result == Path("/custom/opencode")

    def test_xdg_data_home(self, monkeypatch):
        monkeypatch.delenv("OPENCODE_DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", "/xdg/data")
        result = opencode_data_dir()
        assert result == Path("/xdg/data/opencode")

    def test_env_takes_precedence_over_xdg(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_DATA_DIR", "/custom/opencode")
        monkeypatch.setenv("XDG_DATA_HOME", "/xdg/data")
        result = opencode_data_dir()
        assert result == Path("/custom/opencode")
