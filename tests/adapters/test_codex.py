"""Tests for Codex adapter."""

from ctx.adapters.codex import CodexAdapter


class TestDetect:
    def test_detect_with_directory(self, store):
        (store.root / ".codex").mkdir()
        adapter = CodexAdapter(store)
        assert adapter.detect() is True

    def test_detect_neither(self, store, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        adapter = CodexAdapter(store)
        assert adapter.detect() is False


class TestImport:
    def test_import_agents_md(self, store):
        agents = store.root / "AGENTS.md"
        agents.write_text("## Architecture\nClean arch\n")
        adapter = CodexAdapter(store)
        result = adapter.import_context()
        assert result["imported"] >= 1

    def test_import_instructions_md(self, store):
        codex_dir = store.root / ".codex"
        codex_dir.mkdir()
        (codex_dir / "instructions.md").write_text("Always use type hints.\n")
        adapter = CodexAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("codex-instructions")
        assert "type hints" in entry.content

    def test_import_dry_run(self, store):
        agents = store.root / "AGENTS.md"
        agents.write_text("## Test\nContent\n")
        adapter = CodexAdapter(store)
        result = adapter.import_context(dry_run=True)
        assert result["dry_run"] is True
        assert result["imported"] == 0


class TestExport:
    def test_export_agents_md(self, store):
        store.set_knowledge("conventions", "Use black formatter")
        adapter = CodexAdapter(store)
        result = adapter.export_context()
        assert result["exported"] == 1

    def test_export_empty(self, store):
        adapter = CodexAdapter(store)
        result = adapter.export_context()
        assert result["exported"] == 0


class TestMcp:
    def test_mcp_unsupported(self, store):
        adapter = CodexAdapter(store)
        assert adapter.mcp_config_path() is None
        result = adapter.register_mcp()
        assert result["status"] == "unsupported"
