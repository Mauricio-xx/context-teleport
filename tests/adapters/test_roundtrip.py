"""Adapter round-trip tests: export from store -> import into fresh store, verify content."""

from __future__ import annotations

import shutil
from pathlib import Path

import git
import pytest

from ctx.adapters.claude_code import ClaudeCodeAdapter
from ctx.adapters.codex import CodexAdapter
from ctx.adapters.cursor import CursorAdapter
from ctx.adapters.gemini import GeminiAdapter
from ctx.adapters.opencode import OpenCodeAdapter
from ctx.core.frontmatter import build_frontmatter
from ctx.core.store import ContextStore


@pytest.fixture
def source_store(tmp_path: Path) -> ContextStore:
    """Store populated with knowledge, a convention, and a skill."""
    root = tmp_path / "source"
    root.mkdir()
    repo = git.Repo.init(root)
    readme = root / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")

    store = ContextStore(root)
    store.init(project_name="roundtrip-test")
    store.set_knowledge("architecture", "Hexagonal architecture with ports and adapters")
    store.set_knowledge("tech-stack", "Python 3.12, FastMCP, Pydantic")
    store.set_convention("git", "Always rebase, never merge")
    skill_content = build_frontmatter(
        {"name": "run-tests", "description": "Run the test suite"},
        "Execute `pytest tests/ -v` from the project root.\n",
    )
    store.set_skill("run-tests", skill_content)
    return store


def _make_target_store(tmp_path: Path, subdir: str) -> ContextStore:
    """Create a fresh git repo + context store at tmp_path/subdir."""
    root = tmp_path / subdir
    root.mkdir()
    repo = git.Repo.init(root)
    readme = root / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    store = ContextStore(root)
    store.init(project_name="roundtrip-target")
    return store


def _copy_adapter_files(src_root: Path, dst_root: Path, adapter_dir: str):
    """Copy adapter-specific files from source to destination project root."""
    src = src_root / adapter_dir
    if src.exists():
        dst = dst_root / adapter_dir
        shutil.copytree(src, dst, dirs_exist_ok=True)


class TestClaudeCodeRoundtrip:
    def test_roundtrip(self, source_store, tmp_path):
        """Skills round-trip through .claude/skills/. Knowledge goes to CLAUDE.md
        managed section which gets stripped on re-import, so only skills survive."""
        adapter = ClaudeCodeAdapter(source_store)
        result = adapter.export_context()
        assert result["exported"] > 0

        target = _make_target_store(tmp_path, "target")

        # Claude Code exports to CLAUDE.md and .claude/skills/
        for name in ["CLAUDE.md", ".claude"]:
            src = source_store.root / name
            dst = target.root / name
            if src.is_file():
                shutil.copy2(src, dst)
            elif src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)

        target_adapter = ClaudeCodeAdapter(target)
        imp = target_adapter.import_context()
        assert imp["imported"] > 0

        # Skills survive the round-trip via .claude/skills/
        target_skills = {e.name: e.content for e in target.list_skills()}
        assert "run-tests" in target_skills, (
            f"Skill not found after round-trip. Skills: {list(target_skills.keys())}"
        )
        assert "pytest" in target_skills["run-tests"]


class TestCursorRoundtrip:
    def test_roundtrip(self, source_store, tmp_path):
        adapter = CursorAdapter(source_store)
        result = adapter.export_context()
        assert result["exported"] > 0

        target = _make_target_store(tmp_path, "target")
        _copy_adapter_files(source_store.root, target.root, ".cursor")

        target_adapter = CursorAdapter(target)
        imp = target_adapter.import_context()
        assert imp["imported"] > 0

        target_knowledge = {e.key: e.content for e in target.list_knowledge()}
        target_skills = {e.name: e.content for e in target.list_skills()}

        # Convention exported as .cursor/rules/ctx-convention-git.mdc,
        # imported as cursor-rule-ctx-convention-git
        all_content = " ".join(target_knowledge.values())
        assert "rebase" in all_content.lower(), "Convention content lost in round-trip"

        # Knowledge exported as .cursor/rules/ctx-architecture.mdc,
        # imported as cursor-rule-ctx-architecture
        assert "Hexagonal" in all_content or "architecture" in all_content.lower(), (
            "Knowledge content lost in round-trip"
        )

        assert any("run-tests" in name or "run_tests" in name for name in target_skills), (
            f"Skill not found after round-trip. Skills: {list(target_skills.keys())}"
        )


class TestGeminiRoundtrip:
    def test_roundtrip(self, source_store, tmp_path):
        adapter = GeminiAdapter(source_store)
        result = adapter.export_context()
        assert result["exported"] > 0

        target = _make_target_store(tmp_path, "target")
        _copy_adapter_files(source_store.root, target.root, ".gemini")

        target_adapter = GeminiAdapter(target)
        imp = target_adapter.import_context()
        assert imp["imported"] > 0

        target_knowledge = {e.key: e.content for e in target.list_knowledge()}
        target_skills = {e.name: e.content for e in target.list_skills()}

        all_content = " ".join(target_knowledge.values())
        assert "rebase" in all_content.lower(), "Convention content lost in round-trip"
        assert "Hexagonal" in all_content, "Knowledge content lost in round-trip"
        assert any("run-tests" in name for name in target_skills), (
            f"Skill not found after round-trip. Skills: {list(target_skills.keys())}"
        )


class TestOpenCodeRoundtrip:
    def test_roundtrip(self, source_store, tmp_path):
        """Skills round-trip through .opencode/skills/. Knowledge/conventions go
        to AGENTS.md managed section (ctx:start/end) which is skipped on re-import."""
        adapter = OpenCodeAdapter(source_store)
        result = adapter.export_context()
        assert result["exported"] > 0

        target = _make_target_store(tmp_path, "target")
        for name in ["AGENTS.md", ".opencode"]:
            src = source_store.root / name
            dst = target.root / name
            if src.is_file():
                shutil.copy2(src, dst)
            elif src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)

        target_adapter = OpenCodeAdapter(target)
        imp = target_adapter.import_context()
        assert imp["imported"] > 0

        target_skills = {e.name: e.content for e in target.list_skills()}
        assert "run-tests" in target_skills, (
            f"Skill not found after round-trip. Skills: {list(target_skills.keys())}"
        )
        assert "pytest" in target_skills["run-tests"]


class TestCodexRoundtrip:
    def test_roundtrip(self, source_store, tmp_path):
        """Skills round-trip through .codex/skills/. Knowledge/conventions go
        to AGENTS.md managed section (ctx:start/end) which is skipped on re-import."""
        adapter = CodexAdapter(source_store)
        result = adapter.export_context()
        assert result["exported"] > 0

        target = _make_target_store(tmp_path, "target")
        for name in ["AGENTS.md", ".codex"]:
            src = source_store.root / name
            dst = target.root / name
            if src.is_file():
                shutil.copy2(src, dst)
            elif src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)

        target_adapter = CodexAdapter(target)
        imp = target_adapter.import_context()
        assert imp["imported"] > 0

        target_skills = {e.name: e.content for e in target.list_skills()}
        assert "run-tests" in target_skills, (
            f"Skill not found after round-trip. Skills: {list(target_skills.keys())}"
        )
        assert "pytest" in target_skills["run-tests"]
