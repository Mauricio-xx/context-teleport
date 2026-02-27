"""Tests for convention export across all 5 adapters."""

from __future__ import annotations

import pytest



@pytest.fixture
def store_with_conventions(store):
    """Store with conventions and knowledge for export tests."""
    store.set_convention("git", "Always use feature branches.\nCommit early.")
    store.set_convention("env", "No sudo. Use venvs.")
    store.set_knowledge("architecture", "Hexagonal architecture.")
    return store


class TestClaudeCodeExport:
    def test_export_includes_conventions_in_claude_md(self, store_with_conventions):
        from ctx.adapters.claude_code import ClaudeCodeAdapter

        store = store_with_conventions
        claude_md = store.root / "CLAUDE.md"
        claude_md.write_text("# Project\n")

        adapter = ClaudeCodeAdapter(store)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 1

        content = claude_md.read_text()
        assert "### Team Conventions" in content
        assert "#### git" in content
        assert "feature branches" in content
        assert "#### env" in content

    def test_conventions_before_knowledge_in_section(self, store_with_conventions):
        from ctx.adapters.claude_code import ClaudeCodeAdapter

        store = store_with_conventions
        claude_md = store.root / "CLAUDE.md"
        claude_md.write_text("")

        adapter = ClaudeCodeAdapter(store)
        adapter.export_context(dry_run=False)
        content = claude_md.read_text()

        conv_idx = content.index("### Team Conventions")
        know_idx = content.index("### architecture")
        assert conv_idx < know_idx

    def test_conventions_only_export(self, store):
        from ctx.adapters.claude_code import ClaudeCodeAdapter

        store.set_convention("git", "Use branches.")
        adapter = ClaudeCodeAdapter(store)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 1

        content = (store.root / "CLAUDE.md").read_text()
        assert "Team Conventions" in content


class TestCursorExport:
    def test_export_creates_convention_mdc(self, store_with_conventions):
        from ctx.adapters.cursor import CursorAdapter

        adapter = CursorAdapter(store_with_conventions)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 2  # at least 2 conventions

        rules_dir = store_with_conventions.root / ".cursor" / "rules"
        git_rule = rules_dir / "ctx-convention-git.mdc"
        assert git_rule.is_file()
        content = git_rule.read_text()
        assert "alwaysApply" in content
        assert "feature branches" in content

    def test_convention_mdc_separate_from_knowledge(self, store_with_conventions):
        from ctx.adapters.cursor import CursorAdapter

        adapter = CursorAdapter(store_with_conventions)
        adapter.export_context(dry_run=False)

        rules_dir = store_with_conventions.root / ".cursor" / "rules"
        # Convention files have ctx-convention- prefix
        assert (rules_dir / "ctx-convention-git.mdc").is_file()
        # Knowledge files have ctx- prefix
        assert (rules_dir / "ctx-architecture.mdc").is_file()


class TestGeminiExport:
    def test_export_creates_convention_rules(self, store_with_conventions):
        from ctx.adapters.gemini import GeminiAdapter

        adapter = GeminiAdapter(store_with_conventions)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 2

        rules_dir = store_with_conventions.root / ".gemini" / "rules"
        git_rule = rules_dir / "ctx-convention-git.md"
        assert git_rule.is_file()
        assert "feature branches" in git_rule.read_text()

    def test_convention_files_separate_from_knowledge(self, store_with_conventions):
        from ctx.adapters.gemini import GeminiAdapter

        adapter = GeminiAdapter(store_with_conventions)
        adapter.export_context(dry_run=False)

        rules_dir = store_with_conventions.root / ".gemini" / "rules"
        assert (rules_dir / "ctx-convention-git.md").is_file()
        assert (rules_dir / "ctx-architecture.md").is_file()


class TestOpenCodeExport:
    def test_export_conventions_in_agents_md(self, store_with_conventions):
        from ctx.adapters.opencode import OpenCodeAdapter

        adapter = OpenCodeAdapter(store_with_conventions)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 1

        content = (store_with_conventions.root / "AGENTS.md").read_text()
        assert "convention: git" in content
        assert "feature branches" in content

    def test_conventions_before_knowledge_in_agents_md(self, store_with_conventions):
        from ctx.adapters.opencode import OpenCodeAdapter

        adapter = OpenCodeAdapter(store_with_conventions)
        adapter.export_context(dry_run=False)

        content = (store_with_conventions.root / "AGENTS.md").read_text()
        conv_idx = content.index("convention: git")
        know_idx = content.index("architecture")
        assert conv_idx < know_idx


class TestCodexExport:
    def test_export_conventions_in_agents_md(self, store_with_conventions):
        from ctx.adapters.codex import CodexAdapter

        adapter = CodexAdapter(store_with_conventions)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 1

        content = (store_with_conventions.root / "AGENTS.md").read_text()
        assert "convention: git" in content
        assert "feature branches" in content

    def test_conventions_before_knowledge(self, store_with_conventions):
        from ctx.adapters.codex import CodexAdapter

        adapter = CodexAdapter(store_with_conventions)
        adapter.export_context(dry_run=False)

        content = (store_with_conventions.root / "AGENTS.md").read_text()
        conv_idx = content.index("convention: git")
        know_idx = content.index("architecture")
        assert conv_idx < know_idx


class TestConventionsOnlyExport:
    """Test that adapters work when only conventions exist (no knowledge)."""

    def test_cursor_conventions_only(self, store):
        from ctx.adapters.cursor import CursorAdapter

        store.set_convention("git", "branches")
        adapter = CursorAdapter(store)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] == 1

    def test_gemini_conventions_only(self, store):
        from ctx.adapters.gemini import GeminiAdapter

        store.set_convention("git", "branches")
        adapter = GeminiAdapter(store)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] == 1

    def test_opencode_conventions_only(self, store):
        from ctx.adapters.opencode import OpenCodeAdapter

        store.set_convention("git", "branches")
        adapter = OpenCodeAdapter(store)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 1

    def test_codex_conventions_only(self, store):
        from ctx.adapters.codex import CodexAdapter

        store.set_convention("git", "branches")
        adapter = CodexAdapter(store)
        result = adapter.export_context(dry_run=False)
        assert result["exported"] >= 1
