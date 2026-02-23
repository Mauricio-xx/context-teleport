"""Tests for Cursor adapter."""

import json

from ctx.adapters.cursor import CursorAdapter, format_mdc, parse_mdc


class TestMdc:
    def test_parse_mdc(self):
        text = "---\ndescription: Test rule\nalwaysApply: true\n---\n\nRule content here.\n"
        metadata, body = parse_mdc(text)
        assert metadata["description"] == "Test rule"
        assert metadata["alwaysApply"] is True
        assert "Rule content" in body

    def test_parse_mdc_with_globs(self):
        text = '---\nglobs: ["**/*.py", "**/*.js"]\n---\n\nContent.\n'
        metadata, body = parse_mdc(text)
        assert metadata["globs"] == ["**/*.py", "**/*.js"]

    def test_parse_mdc_no_frontmatter(self):
        text = "Just plain markdown content."
        metadata, body = parse_mdc(text)
        assert metadata == {}
        assert body == text

    def test_format_mdc(self):
        metadata = {"description": "My rule", "alwaysApply": True}
        result = format_mdc(metadata, "Rule body")
        assert result.startswith("---")
        assert "description: My rule" in result
        assert "alwaysApply: true" in result
        assert "Rule body" in result

    def test_mdc_roundtrip(self):
        metadata = {"description": "Test", "alwaysApply": False}
        content = "Some rule content"
        formatted = format_mdc(metadata, content)
        parsed_meta, parsed_body = parse_mdc(formatted)
        assert parsed_meta["description"] == "Test"
        assert parsed_meta["alwaysApply"] is False
        assert "Some rule content" in parsed_body


class TestDetect:
    def test_detect_with_cursor_dir(self, store):
        (store.root / ".cursor").mkdir()
        adapter = CursorAdapter(store)
        assert adapter.detect() is True

    def test_detect_with_cursorrules(self, store):
        (store.root / ".cursorrules").write_text("rules here")
        adapter = CursorAdapter(store)
        assert adapter.detect() is True

    def test_detect_neither(self, store):
        adapter = CursorAdapter(store)
        assert adapter.detect() is False


class TestImport:
    def test_import_mdc_rules(self, store):
        rules_dir = store.root / ".cursor" / "rules"
        rules_dir.mkdir(parents=True)
        mdc = "---\ndescription: Test\nalwaysApply: true\n---\n\nAlways write tests.\n"
        (rules_dir / "testing.mdc").write_text(mdc)
        adapter = CursorAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("cursor-rule-testing")
        assert "write tests" in entry.content

    def test_import_legacy_cursorrules(self, store):
        (store.root / ".cursorrules").write_text("Use TypeScript.\n")
        adapter = CursorAdapter(store)
        result = adapter.import_context()
        assert result["imported"] == 1
        entry = store.get_knowledge("cursorrules")
        assert "TypeScript" in entry.content


class TestExport:
    def test_export_mdc_format(self, store):
        store.set_knowledge("arch", "Hexagonal architecture")
        adapter = CursorAdapter(store)
        result = adapter.export_context()
        assert result["exported"] == 1
        rule = store.root / ".cursor" / "rules" / "ctx-arch.mdc"
        assert rule.is_file()
        content = rule.read_text()
        assert "---" in content
        assert "Hexagonal" in content


class TestMcp:
    def test_register(self, store):
        adapter = CursorAdapter(store)
        result = adapter.register_mcp()
        assert result["status"] == "registered"
        config = json.loads((store.root / ".cursor" / "mcp.json").read_text())
        assert "context-teleport" in config["mcpServers"]

    def test_unregister(self, store):
        adapter = CursorAdapter(store)
        adapter.register_mcp()
        result = adapter.unregister_mcp()
        assert result["status"] == "unregistered"
