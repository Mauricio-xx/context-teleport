"""Tests for Gemini adapter."""

import json

from ctx.adapters.gemini import GeminiAdapter


class TestDetect:
    def test_detect_with_gemini_dir(self, store):
        (store.root / ".gemini").mkdir()
        adapter = GeminiAdapter(store)
        assert adapter.detect() is True

    def test_detect_with_gemini_md(self, store):
        (store.root / "GEMINI.md").write_text("# Gemini Config\n")
        adapter = GeminiAdapter(store)
        assert adapter.detect() is True

    def test_detect_neither(self, store):
        adapter = GeminiAdapter(store)
        assert adapter.detect() is False


class TestImport:
    def test_import_rules(self, store):
        rules_dir = store.root / ".gemini" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "coding.md").write_text("Always write tests.\n")
        (rules_dir / "style.md").write_text("Use PEP 8.\n")
        adapter = GeminiAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 2

    def test_import_styleguide(self, store):
        gemini_dir = store.root / ".gemini"
        gemini_dir.mkdir()
        (gemini_dir / "STYLEGUIDE.md").write_text("Follow Google style.\n")
        adapter = GeminiAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("gemini-styleguide")
        assert "Google style" in entry.content

    def test_import_gemini_md(self, store):
        (store.root / "GEMINI.md").write_text("Use structured output.\n")
        adapter = GeminiAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1

    def test_import_dry_run(self, store):
        rules_dir = store.root / ".gemini" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "test.md").write_text("Content\n")
        adapter = GeminiAdapter(store)
        result = adapter.import_context(dry_run=True)
        assert result["dry_run"] is True
        assert result["imported"] == 0


class TestExport:
    def test_export_as_rules(self, store):
        store.set_knowledge("arch", "Hexagonal architecture")
        adapter = GeminiAdapter(store)
        result = adapter.export_context()
        assert result["exported"] == 1
        rule = store.root / ".gemini" / "rules" / "ctx-arch.md"
        assert rule.is_file()
        assert "Hexagonal" in rule.read_text()

    def test_export_empty(self, store):
        adapter = GeminiAdapter(store)
        result = adapter.export_context()
        assert result["exported"] == 0


class TestMcp:
    def test_register_creates_config(self, store):
        adapter = GeminiAdapter(store)
        result = adapter.register_mcp()
        assert result["status"] == "registered"
        config_path = store.root / ".gemini" / "settings.json"
        assert config_path.is_file()
        config = json.loads(config_path.read_text())
        assert "context-teleport" in config["mcpServers"]
        entry = config["mcpServers"]["context-teleport"]
        assert entry["command"] == "uvx"
        assert entry["args"] == ["context-teleport"]

    def test_register_creates_parent_dir(self, store):
        adapter = GeminiAdapter(store)
        assert not (store.root / ".gemini").exists()
        result = adapter.register_mcp()
        assert result["status"] == "registered"
        assert (store.root / ".gemini" / "settings.json").is_file()

    def test_register_is_idempotent(self, store):
        adapter = GeminiAdapter(store)
        adapter.register_mcp()
        adapter.register_mcp()
        config_path = store.root / ".gemini" / "settings.json"
        config = json.loads(config_path.read_text())
        assert len(config["mcpServers"]) == 1

    def test_unregister(self, store):
        adapter = GeminiAdapter(store)
        adapter.register_mcp()
        result = adapter.unregister_mcp()
        assert result["status"] == "unregistered"
        config_path = store.root / ".gemini" / "settings.json"
        config = json.loads(config_path.read_text())
        assert "context-teleport" not in config["mcpServers"]

    def test_mcp_config_path_always_returns(self, store):
        adapter = GeminiAdapter(store)
        path = adapter.mcp_config_path()
        assert path is not None
        assert path.name == "settings.json"
