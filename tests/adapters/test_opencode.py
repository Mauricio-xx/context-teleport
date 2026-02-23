"""Tests for OpenCode adapter."""

import json
import sqlite3

from ctx.adapters.opencode import OpenCodeAdapter


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
        adapter = OpenCodeAdapter(store)
        result = adapter.import_context(dry_run=True)
        assert result["dry_run"] is True
        assert result["imported"] == 0
        assert len(result["items"]) == 1

    def test_import_sqlite_sessions(self, store):
        db_dir = store.root / ".opencode"
        db_dir.mkdir()
        db_path = db_dir / "opencode.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE sessions (id TEXT, title TEXT, created_at TEXT)")
        conn.execute("INSERT INTO sessions VALUES ('abc123', 'Test session', '2025-01-01')")
        conn.commit()
        conn.close()

        adapter = OpenCodeAdapter(store)
        result = adapter.import_context(dry_run=True)
        session_items = [i for i in result["items"] if i["type"] == "session"]
        assert len(session_items) == 1


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


class TestMcp:
    def test_register(self, store):
        adapter = OpenCodeAdapter(store)
        result = adapter.register_mcp()
        assert result["status"] == "registered"
        config = json.loads((store.root / "opencode.json").read_text())
        assert "context-teleport" in config["mcpServers"]

    def test_unregister(self, store):
        adapter = OpenCodeAdapter(store)
        adapter.register_mcp()
        result = adapter.unregister_mcp()
        assert result["status"] == "unregistered"
