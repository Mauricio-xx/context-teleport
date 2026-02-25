"""Tests for Claude Code adapter."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ctx.adapters.claude_code import ClaudeCodeAdapter, _slugify, _strip_ctx_section
from ctx.core.scope import Scope
from ctx.core.store import ContextStore


class TestSlugify:
    def test_basic(self):
        assert _slugify("Use PostgreSQL over SQLite") == "use-postgresql-over-sqlite"

    def test_special_chars(self):
        assert _slugify("Hello, World!") == "hello-world"

    def test_empty(self):
        assert _slugify("") == "untitled"


class TestStripCtxSection:
    def test_removes_section(self):
        text = "Before\n\n## Team Context (managed by ctx)\nStuff\n<!-- end ctx managed -->\n\nAfter"
        result = _strip_ctx_section(text)
        assert "Team Context" not in result
        assert "Before" in result
        assert "After" in result

    def test_no_section(self):
        text = "Just normal content"
        assert _strip_ctx_section(text) == text


class TestParseMemory:
    def test_sections(self, store):
        adapter = ClaudeCodeAdapter(store)
        memory = "# Architecture\nHexagonal pattern\n\n## Conventions\nUse ruff\n"
        entries = adapter._parse_memory_into_knowledge(memory)
        assert len(entries) == 2
        assert entries[0][0] == "architecture"
        assert "Hexagonal" in entries[0][1]
        assert entries[1][0] == "conventions"

    def test_no_headers(self, store):
        adapter = ClaudeCodeAdapter(store)
        entries = adapter._parse_memory_into_knowledge("Just plain text")
        assert len(entries) == 1
        assert entries[0][0] == "memory"


class TestImportExport:
    def test_import_dry_run_with_claude_md(self, store):
        # Create a CLAUDE.md in the project root
        claude_md = store.root / "CLAUDE.md"
        claude_md.write_text("# My Project\n\nSome instructions.\n")

        adapter = ClaudeCodeAdapter(store)
        result = adapter.import_context(dry_run=True)
        assert result["dry_run"] is True
        assert result["imported"] == 0
        items = result["items"]
        # Should find the CLAUDE.md
        sources = [i["source"] for i in items]
        assert "CLAUDE.md" in sources

    def test_import_writes_to_store(self, store):
        claude_md = store.root / "CLAUDE.md"
        claude_md.write_text("# Project\n\nKey instructions here.\n")

        adapter = ClaudeCodeAdapter(store)
        result = adapter.import_context(dry_run=False)
        assert result["imported"] >= 1

        entry = store.get_knowledge("project-instructions")
        assert entry is not None
        assert "Key instructions" in entry.content

    def test_export_creates_managed_section(self, populated_store):
        adapter = ClaudeCodeAdapter(populated_store)
        # Create a CLAUDE.md first
        claude_md = populated_store.root / "CLAUDE.md"
        claude_md.write_text("# My Project\n\nOriginal content.\n")

        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 1

        content = claude_md.read_text()
        assert "## Team Context (managed by ctx)" in content
        assert "Original content" in content  # Original preserved
        assert "architecture" in content.lower()

    def test_export_dry_run(self, populated_store):
        adapter = ClaudeCodeAdapter(populated_store)
        result = adapter.export_context(dry_run=True)
        assert result["dry_run"] is True
        assert result["exported"] == 0
        assert len(result["items"]) > 0

    def test_export_excludes_private(self, store):
        store.set_knowledge("public-arch", "Public architecture notes")
        store.set_knowledge("private-notes", "My private notes", scope=Scope.private)

        adapter = ClaudeCodeAdapter(store)
        claude_md = store.root / "CLAUDE.md"
        claude_md.write_text("# Project\n")

        result = adapter.export_context(dry_run=False)
        content = claude_md.read_text()
        assert "public-arch" in content
        assert "private-notes" not in content

    def test_export_excludes_ephemeral(self, store):
        store.set_knowledge("public-info", "Public info")
        store.set_knowledge("scratch", "Ephemeral scratch", scope=Scope.ephemeral)

        adapter = ClaudeCodeAdapter(store)
        claude_md = store.root / "CLAUDE.md"
        claude_md.write_text("# Project\n")

        adapter.export_context(dry_run=False)
        content = claude_md.read_text()
        assert "public-info" in content
        assert "scratch" not in content


class TestSkillImportExport:
    def _skill_content(self, name="deploy", desc="Deploy to staging"):
        return f"---\nname: {name}\ndescription: {desc}\n---\n\nRun the deploy script.\n"

    def test_import_skills(self, store):
        skills_dir = store.root / ".claude" / "skills" / "deploy"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(self._skill_content())

        adapter = ClaudeCodeAdapter(store)
        result = adapter.import_context(dry_run=False)
        assert result["imported"] >= 1

        skill_items = [i for i in result["items"] if i["type"] == "skill"]
        assert len(skill_items) == 1
        assert skill_items[0]["key"] == "deploy"

        entry = store.get_skill("deploy")
        assert entry is not None
        assert entry.name == "deploy"

    def test_import_skills_dry_run(self, store):
        skills_dir = store.root / ".claude" / "skills" / "lint"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(self._skill_content("lint", "Run linter"))

        adapter = ClaudeCodeAdapter(store)
        result = adapter.import_context(dry_run=True)
        assert result["dry_run"] is True
        assert result["imported"] == 0
        skill_items = [i for i in result["items"] if i["type"] == "skill"]
        assert len(skill_items) == 1

        # Store should not have the skill
        assert store.get_skill("lint") is None

    def test_export_skills(self, store):
        store.set_skill("deploy", self._skill_content())
        claude_md = store.root / "CLAUDE.md"
        claude_md.write_text("# Project\n")

        adapter = ClaudeCodeAdapter(store)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 2  # CLAUDE.md + skill

        skill_path = store.root / ".claude" / "skills" / "deploy" / "SKILL.md"
        assert skill_path.is_file()
        assert "Deploy to staging" in skill_path.read_text()

    def test_export_skills_only_public(self, store):
        store.set_skill("pub", self._skill_content("pub", "Public skill"))
        store.set_skill("priv", self._skill_content("priv", "Private skill"), scope=Scope.private)
        claude_md = store.root / "CLAUDE.md"
        claude_md.write_text("# Project\n")

        adapter = ClaudeCodeAdapter(store)
        adapter.export_context(dry_run=False)

        assert (store.root / ".claude" / "skills" / "pub" / "SKILL.md").is_file()
        assert not (store.root / ".claude" / "skills" / "priv" / "SKILL.md").is_file()
