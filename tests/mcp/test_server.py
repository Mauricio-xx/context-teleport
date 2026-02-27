"""Tests for the MCP server tools, resources, and prompts."""

from __future__ import annotations

import json
import os

import git
import pytest

from ctx.core.conflicts import ConflictEntry, ConflictReport
from ctx.core.store import ContextStore
from ctx.core.scope import Scope
from ctx.sync.git_sync import GitSync
from ctx.utils.paths import STORE_DIR
from ctx.mcp.server import (
    _FALLBACK_INSTRUCTIONS,
    _generate_instructions,
    mcp,
    set_store,
    context_search,
    context_add_knowledge,
    context_remove_knowledge,
    context_add_skill,
    context_remove_skill,
    context_record_decision,
    context_update_state,
    context_append_session,
    context_sync_push,
    context_sync_pull,
    context_get,
    context_set,
    context_get_scope,
    context_set_scope,
    context_merge_status,
    context_resolve_conflict,
    context_conflict_detail,
    context_merge_finalize,
    context_merge_abort,
    resource_manifest,
    resource_knowledge,
    resource_knowledge_item,
    resource_decisions,
    resource_decision_item,
    resource_state,
    resource_history,
    resource_summary,
    resource_skills,
    resource_skill_item,
    context_onboarding,
    context_handoff,
    context_review_decisions,
    context_resolve_conflicts,
)


@pytest.fixture
def store(tmp_path):
    """Create and initialize a ContextStore in a temp directory."""
    s = ContextStore(tmp_path)
    s.init(project_name="test-mcp-project")
    set_store(s)
    yield s
    set_store(None)


@pytest.fixture
def git_store(tmp_path):
    """ContextStore in a git repo (needed for sync tool tests)."""
    repo = git.Repo.init(tmp_path)
    (tmp_path / "README.md").write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")

    s = ContextStore(tmp_path)
    s.init(project_name="test-mcp-git")
    repo.index.add([STORE_DIR])
    repo.index.commit("init context store")

    set_store(s)
    yield s
    set_store(None)


class TestAutoInit:
    """Auto-init when MCP server starts in a git repo without .context-teleport/."""

    def test_auto_init_creates_store(self, tmp_path):
        """_get_store() should auto-init when .context-teleport/ is missing."""
        from ctx.mcp.server import _get_store
        import ctx.mcp.server as srv

        # Create a bare git repo (no .context-teleport/)
        repo = git.Repo.init(tmp_path)
        (tmp_path / "README.md").write_text("# Test\n")
        repo.index.add(["README.md"])
        repo.index.commit("initial")

        # Reset module state and point to our tmp dir
        old_store = srv._store
        srv._store = None
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            store = _get_store()
            assert store.initialized
            assert (tmp_path / ".context-teleport" / "manifest.json").is_file()
            manifest = store.read_manifest()
            assert manifest.project.name == tmp_path.name
        finally:
            os.chdir(old_cwd)
            srv._store = old_store

    def test_auto_init_uses_directory_name(self, tmp_path):
        """Auto-init should use the directory name as project name."""
        from ctx.mcp.server import _get_store
        import ctx.mcp.server as srv

        repo = git.Repo.init(tmp_path)
        (tmp_path / "README.md").write_text("# Test\n")
        repo.index.add(["README.md"])
        repo.index.commit("initial")

        old_store = srv._store
        srv._store = None
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            store = _get_store()
            manifest = store.read_manifest()
            assert manifest.project.name == tmp_path.name
        finally:
            os.chdir(old_cwd)
            srv._store = old_store


    def test_auto_init_blocked_by_env(self, tmp_path):
        """CTX_NO_AUTO_INIT=1 should prevent auto-init and raise RuntimeError."""
        from ctx.mcp.server import _get_store
        import ctx.mcp.server as srv

        repo = git.Repo.init(tmp_path)
        (tmp_path / "README.md").write_text("# Test\n")
        repo.index.add(["README.md"])
        repo.index.commit("initial")

        old_store = srv._store
        srv._store = None
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        old_env = os.environ.get("CTX_NO_AUTO_INIT")
        os.environ["CTX_NO_AUTO_INIT"] = "1"
        try:
            with pytest.raises(RuntimeError, match="CTX_NO_AUTO_INIT"):
                _get_store()
            assert not (tmp_path / ".context-teleport").exists()
        finally:
            os.chdir(old_cwd)
            srv._store = old_store
            if old_env is None:
                os.environ.pop("CTX_NO_AUTO_INIT", None)
            else:
                os.environ["CTX_NO_AUTO_INIT"] = old_env


class TestResources:
    def test_manifest(self, store):
        result = json.loads(resource_manifest())
        assert result["project"]["name"] == "test-mcp-project"
        assert result["schema_version"] == "0.4.0"

    def test_knowledge_empty(self, store):
        result = json.loads(resource_knowledge())
        assert result == []

    def test_knowledge_with_entries(self, store):
        store.set_knowledge("arch", "Monolith pattern")
        store.set_knowledge("stack", "Python + FastMCP")
        result = json.loads(resource_knowledge())
        assert len(result) == 2
        keys = {e["key"] for e in result}
        assert keys == {"arch", "stack"}

    def test_knowledge_item_found(self, store):
        store.set_knowledge("arch", "Event-driven architecture")
        result = json.loads(resource_knowledge_item("arch"))
        assert result["key"] == "arch"
        assert "Event-driven" in result["content"]

    def test_knowledge_item_not_found(self, store):
        result = json.loads(resource_knowledge_item("nonexistent"))
        assert "error" in result

    def test_decisions_empty(self, store):
        result = json.loads(resource_decisions())
        assert result == []

    def test_decisions_with_entries(self, store):
        store.add_decision(title="Use PostgreSQL", context="Need relational DB")
        result = json.loads(resource_decisions())
        assert len(result) == 1
        assert result[0]["title"] == "Use PostgreSQL"

    def test_decision_item(self, store):
        store.add_decision(title="Use MCP", decision_text="Expose via MCP protocol")
        result = json.loads(resource_decision_item("1"))
        assert result["title"] == "Use MCP"
        assert "MCP protocol" in result["decision"]

    def test_decision_item_not_found(self, store):
        result = json.loads(resource_decision_item("999"))
        assert "error" in result

    def test_state(self, store):
        result = json.loads(resource_state())
        assert result["current_task"] == ""

    def test_history_empty(self, store):
        result = json.loads(resource_history())
        assert result == []

    def test_summary(self, store):
        store.set_knowledge("arch", "Some architecture notes")
        result = json.loads(resource_summary())
        assert result["project"] == "test-mcp-project"
        assert result["knowledge_count"] == 1

    def test_skills_empty(self, store):
        result = json.loads(resource_skills())
        assert result == []

    def test_skills_with_entries(self, store):
        store.set_skill("deploy", "---\nname: deploy\ndescription: Deploy to staging\n---\n\nRun deploy.\n")
        store.set_skill("lint", "---\nname: lint\ndescription: Run linter\n---\n\nRun ruff.\n")
        result = json.loads(resource_skills())
        assert len(result) == 2
        names = {e["name"] for e in result}
        assert names == {"deploy", "lint"}

    def test_skill_item_found(self, store):
        store.set_skill("deploy", "---\nname: deploy\ndescription: Deploy to staging\n---\n\nRun deploy.\n")
        result = json.loads(resource_skill_item("deploy"))
        assert result["name"] == "deploy"
        assert "Deploy to staging" in result["description"]

    def test_skill_item_not_found(self, store):
        result = json.loads(resource_skill_item("nonexistent"))
        assert "error" in result


class TestTools:
    def test_search_empty(self, store):
        result = json.loads(context_search("nonexistent"))
        assert result == []

    def test_search_with_results(self, store):
        store.set_knowledge("arch", "Microservices with event bus")
        result = json.loads(context_search("microservices"))
        assert len(result) > 0
        assert result[0]["key"] == "arch"

    def test_add_knowledge(self, store):
        result = json.loads(context_add_knowledge("tech-stack", "Python 3.12"))
        assert result["status"] == "ok"
        assert result["key"] == "tech-stack"
        entry = store.get_knowledge("tech-stack")
        assert entry is not None
        assert entry.content == "Python 3.12"

    def test_remove_knowledge(self, store):
        store.set_knowledge("temp", "temporary content")
        result = json.loads(context_remove_knowledge("temp"))
        assert result["status"] == "removed"
        assert store.get_knowledge("temp") is None

    def test_remove_knowledge_not_found(self, store):
        result = json.loads(context_remove_knowledge("ghost"))
        assert result["status"] == "not_found"

    def test_add_skill(self, store):
        result = json.loads(context_add_skill("deploy", "Deploy to staging", "Run the deploy script."))
        assert result["status"] == "ok"
        assert result["name"] == "deploy"
        entry = store.get_skill("deploy")
        assert entry is not None
        assert "Deploy to staging" in entry.description
        assert "deploy script" in entry.content

    def test_add_skill_with_scope(self, store):
        result = json.loads(context_add_skill("priv-skill", "Private", "Secret instructions.", scope="private"))
        assert result["status"] == "ok"
        assert store.get_skill_scope("priv-skill") == Scope.private

    def test_remove_skill(self, store):
        store.set_skill("temp", "---\nname: temp\ndescription: Temp\n---\n\nBody.\n")
        result = json.loads(context_remove_skill("temp"))
        assert result["status"] == "removed"
        assert store.get_skill("temp") is None

    def test_remove_skill_not_found(self, store):
        result = json.loads(context_remove_skill("ghost"))
        assert result["status"] == "not_found"

    def test_record_decision(self, store):
        result = json.loads(
            context_record_decision(
                title="Use FastMCP",
                context="Need MCP server",
                decision="Use FastMCP SDK",
                consequences="Tied to Python SDK",
            )
        )
        assert result["status"] == "ok"
        assert result["id"] == 1
        dec = store.get_decision("1")
        assert dec is not None
        assert dec.title == "Use FastMCP"

    def test_update_state(self, store):
        result = json.loads(context_update_state(current_task="Building MCP server"))
        assert result["status"] == "ok"
        state = store.read_active_state()
        assert state.current_task == "Building MCP server"

    def test_update_state_with_blockers(self, store):
        result = json.loads(
            context_update_state(current_task="Testing", blockers="CI broken, deps missing")
        )
        assert result["status"] == "ok"
        state = store.read_active_state()
        assert state.blockers == ["CI broken", "deps missing"]

    def test_append_session(self, store):
        result = json.loads(
            context_append_session(
                agent="claude-code",
                summary="Implemented MCP server",
                knowledge_added="mcp-design",
            )
        )
        assert result["status"] == "ok"
        sessions = store.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].agent == "claude-code"

    def test_context_get(self, store):
        store.set_knowledge("arch", "Layered architecture")
        result = json.loads(context_get("knowledge.arch"))
        assert "Layered architecture" in result

    def test_context_get_not_found(self, store):
        result = json.loads(context_get("knowledge.nonexistent"))
        assert "error" in result

    def test_context_set(self, store):
        result = json.loads(context_set("knowledge.new-entry", "New content"))
        assert result["status"] == "ok"
        entry = store.get_knowledge("new-entry")
        assert entry is not None
        assert entry.content == "New content"

    def test_context_set_invalid(self, store):
        result = json.loads(context_set("manifest.name", "nope"))
        assert result["status"] == "error"

    def test_sync_push_no_git(self, store):
        # Store is in tmp_path which has no git repo
        result = json.loads(context_sync_push())
        assert result["status"] == "error"

    def test_sync_pull_no_git(self, store):
        result = json.loads(context_sync_pull())
        assert result["status"] == "error"

    def test_add_knowledge_includes_agent(self, store):
        """MCP tool writes should include agent attribution."""
        import os
        old = os.environ.get("MCP_CALLER")
        os.environ["MCP_CALLER"] = "mcp:claude-code"
        try:
            result = json.loads(context_add_knowledge("attr-test", "Test content"))
            assert result["status"] == "ok"
            entry = store.get_knowledge("attr-test")
            assert entry.author == "mcp:claude-code"
        finally:
            if old is None:
                os.environ.pop("MCP_CALLER", None)
            else:
                os.environ["MCP_CALLER"] = old

    def test_add_knowledge_default_agent(self, store):
        """Without MCP_CALLER env, falls back to mcp:unknown."""
        import os
        old = os.environ.pop("MCP_CALLER", None)
        try:
            result = json.loads(context_add_knowledge("default-agent", "Content"))
            assert result["status"] == "ok"
            entry = store.get_knowledge("default-agent")
            assert entry.author == "mcp:unknown"
        finally:
            if old is not None:
                os.environ["MCP_CALLER"] = old


class TestPrompts:
    def test_onboarding_empty(self, store):
        result = context_onboarding()
        assert "test-mcp-project" in result

    def test_onboarding_with_content(self, store):
        store.set_knowledge("arch", "Microservices")
        store.add_decision(title="Use Python")
        result = context_onboarding()
        assert "Microservices" in result
        assert "Use Python" in result

    def test_onboarding_with_skills(self, store):
        store.set_skill("deploy", "---\nname: deploy\ndescription: Deploy to staging\n---\n\nRun deploy.\n")
        result = context_onboarding()
        assert "deploy" in result
        assert "Deploy to staging" in result

    def test_onboarding_truncates_knowledge(self, store):
        """Onboarding should truncate knowledge when exceeding MAX_ONBOARDING_KNOWLEDGE."""
        from ctx.mcp.server import MAX_ONBOARDING_KNOWLEDGE

        for i in range(MAX_ONBOARDING_KNOWLEDGE + 5):
            store.set_knowledge(f"entry-{i:03d}", f"Content for entry {i}")

        result = context_onboarding()
        assert "... and 5 more" in result
        assert "context://knowledge" in result
        # First entries should be present
        assert "entry-000" in result
        # Entries beyond the limit should not have content in onboarding
        assert f"Content for entry {MAX_ONBOARDING_KNOWLEDGE + 4}" not in result

    def test_onboarding_truncates_decisions(self, store):
        """Onboarding should truncate decisions when exceeding MAX_ONBOARDING_DECISIONS."""
        from ctx.mcp.server import MAX_ONBOARDING_DECISIONS

        for i in range(MAX_ONBOARDING_DECISIONS + 3):
            store.add_decision(title=f"Decision {i:03d}")

        result = context_onboarding()
        assert "... and 3 more" in result
        assert "context://decisions" in result

    def test_handoff(self, store):
        from ctx.core.schema import ActiveState

        state = ActiveState(current_task="Building MCP", blockers=["Tests failing"])
        store.write_active_state(state)
        result = context_handoff()
        assert "Building MCP" in result
        assert "Tests failing" in result

    def test_review_decisions_empty(self, store):
        result = context_review_decisions()
        assert "No decisions" in result

    def test_review_decisions_with_content(self, store):
        store.add_decision(
            title="Use AGPL-3.0",
            context="Need copyleft",
            decision_text="AGPL with CLA",
            consequences="Must open source",
        )
        result = context_review_decisions()
        assert "Use AGPL-3.0" in result
        assert "copyleft" in result


class TestScopeTools:
    def test_add_knowledge_with_scope(self, store):
        result = json.loads(context_add_knowledge("notes", "My private notes", scope="private"))
        assert result["status"] == "ok"
        assert store.get_knowledge_scope("notes") == Scope.private

    def test_record_decision_with_scope(self, store):
        result = json.loads(context_record_decision(title="Internal", scope="private"))
        assert result["status"] == "ok"
        scope = store.get_decision_scope(str(result["id"]))
        assert scope == Scope.private

    def test_get_scope_knowledge(self, store):
        store.set_knowledge("arch", "Architecture", scope=Scope.private)
        result = json.loads(context_get_scope("knowledge", "arch"))
        assert result["scope"] == "private"

    def test_get_scope_decision(self, store):
        store.add_decision(title="Public Dec")
        result = json.loads(context_get_scope("decision", "1"))
        assert result["scope"] == "public"

    def test_set_scope(self, store):
        store.set_knowledge("arch", "Architecture")
        result = json.loads(context_set_scope("knowledge", "arch", "ephemeral"))
        assert result["status"] == "ok"
        assert store.get_knowledge_scope("arch") == Scope.ephemeral

    def test_get_scope_skill(self, store):
        store.set_skill("deploy", "---\nname: deploy\ndescription: Deploy\n---\n\nBody.\n", scope=Scope.private)
        result = json.loads(context_get_scope("skill", "deploy"))
        assert result["scope"] == "private"

    def test_set_scope_skill(self, store):
        store.set_skill("deploy", "---\nname: deploy\ndescription: Deploy\n---\n\nBody.\n")
        result = json.loads(context_set_scope("skill", "deploy", "ephemeral"))
        assert result["status"] == "ok"
        assert store.get_skill_scope("deploy") == Scope.ephemeral

    def test_knowledge_resource_includes_scope(self, store):
        store.set_knowledge("pub", "Public entry")
        store.set_knowledge("priv", "Private entry", scope=Scope.private)
        result = json.loads(resource_knowledge())
        scopes = {e["key"]: e["scope"] for e in result}
        assert scopes["pub"] == "public"
        assert scopes["priv"] == "private"

    def test_onboarding_only_public(self, store):
        store.set_knowledge("pub", "Public knowledge")
        store.set_knowledge("priv", "Secret knowledge", scope=Scope.private)
        result = context_onboarding()
        assert "Public knowledge" in result
        assert "Secret knowledge" not in result


class TestSyncTools:
    """Tests for conflict resolution MCP tools (disk-backed state)."""

    def test_sync_pull_with_strategy_param(self, git_store):
        result = json.loads(context_sync_pull(strategy="ours"))
        assert result["status"] == "no_remote"

    def test_sync_pull_invalid_strategy(self, git_store):
        result = json.loads(context_sync_pull(strategy="invalid"))
        assert result["status"] == "error"
        assert "Invalid strategy" in result["error"]

    def test_merge_status_clean(self, git_store):
        result = json.loads(context_merge_status())
        assert result["status"] == "clean"

    def test_merge_status_with_pending(self, git_store):
        gs = GitSync(git_store.root)
        report = ConflictReport(conflicts=[
            ConflictEntry("knowledge/arch.md", "ours", "theirs", "base"),
        ])
        gs.save_pending_report(report)

        result = json.loads(context_merge_status())
        assert result["status"] == "conflicts"
        assert result["conflict_id"] == report.conflict_id
        assert result["report"]["unresolved"] == 1

    def test_conflict_detail_no_pending(self, git_store):
        result = json.loads(context_conflict_detail("knowledge/arch.md"))
        assert result["status"] == "error"
        assert "No pending" in result["error"]

    def test_conflict_detail_returns_full_content(self, git_store):
        gs = GitSync(git_store.root)
        report = ConflictReport(conflicts=[
            ConflictEntry(
                "knowledge/arch.md",
                "## Backend\nDjango\n",
                "## Backend\nFastAPI\n",
                "## Backend\nFlask\n",
            ),
        ])
        gs.save_pending_report(report)

        result = json.loads(context_conflict_detail("knowledge/arch.md"))
        assert result["file_path"] == "knowledge/arch.md"
        assert result["ours_content"] == "## Backend\nDjango\n"
        assert result["theirs_content"] == "## Backend\nFastAPI\n"
        assert result["base_content"] == "## Backend\nFlask\n"
        assert "diff" in result
        assert "section_analysis" in result

    def test_conflict_detail_not_found(self, git_store):
        gs = GitSync(git_store.root)
        report = ConflictReport(conflicts=[
            ConflictEntry("knowledge/arch.md", "ours", "theirs"),
        ])
        gs.save_pending_report(report)

        result = json.loads(context_conflict_detail("knowledge/other.md"))
        assert result["status"] == "error"

    def test_resolve_conflict_persists(self, git_store):
        gs = GitSync(git_store.root)
        report = ConflictReport(conflicts=[
            ConflictEntry("knowledge/arch.md", "ours", "theirs"),
            ConflictEntry("knowledge/stack.md", "ours2", "theirs2"),
        ])
        gs.save_pending_report(report)

        result = json.loads(context_resolve_conflict("knowledge/arch.md", "merged content"))
        assert result["status"] == "resolved"
        assert result["remaining"] == 1

        # Verify persisted
        reloaded = gs.load_pending_report()
        assert reloaded.conflicts[0].resolved is True
        assert reloaded.conflicts[0].resolution == "merged content"

    def test_resolve_conflict_no_pending(self, git_store):
        result = json.loads(context_resolve_conflict("knowledge/arch.md", "content"))
        assert result["status"] == "error"
        assert "No pending" in result["error"]

    def test_merge_abort(self, git_store):
        gs = GitSync(git_store.root)
        gs.save_pending_report(ConflictReport(conflicts=[
            ConflictEntry("knowledge/arch.md", "ours", "theirs"),
        ]))

        result = json.loads(context_merge_abort())
        assert result["status"] == "aborted"
        assert not gs.has_pending_conflicts()

    def test_merge_abort_no_pending(self, git_store):
        result = json.loads(context_merge_abort())
        assert result["status"] == "error"

    def test_merge_finalize_no_pending(self, git_store):
        result = json.loads(context_merge_finalize())
        assert result["status"] == "error"
        assert "No pending" in result["error"]


class TestConflictResolutionPrompt:
    def test_resolve_conflicts_no_pending(self, git_store):
        result = context_resolve_conflicts()
        assert "No pending" in result

    def test_resolve_conflicts_with_pending(self, git_store):
        gs = GitSync(git_store.root)
        report = ConflictReport(conflicts=[
            ConflictEntry("knowledge/arch.md", "ours-long-content", "theirs-long-content"),
            ConflictEntry("knowledge/stack.md", "ours2", "theirs2"),
        ])
        gs.save_pending_report(report)

        result = context_resolve_conflicts()
        assert "Merge Conflict Resolution Guide" in result
        assert report.conflict_id in result
        assert "knowledge/arch.md" in result
        assert "knowledge/stack.md" in result
        assert "context_conflict_detail" in result
        assert "context_resolve_conflict" in result
        assert "context_merge_finalize" in result

    def test_resolve_conflicts_no_git(self, store):
        result = context_resolve_conflicts()
        assert "Error" in result


class TestMCPRegistration:
    """Verify the FastMCP app has all expected tools/resources/prompts registered."""

    def test_tools_registered(self, store):
        tool_names = set(mcp._tool_manager._tools.keys())
        expected = {
            "context_search",
            "context_add_knowledge",
            "context_remove_knowledge",
            "context_add_skill",
            "context_remove_skill",
            "context_record_decision",
            "context_update_state",
            "context_append_session",
            "context_sync_push",
            "context_sync_pull",
            "context_get",
            "context_set",
            "context_get_scope",
            "context_set_scope",
            "context_merge_status",
            "context_resolve_conflict",
            "context_conflict_detail",
            "context_merge_finalize",
            "context_merge_abort",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

    def test_tool_count(self, store):
        from tests.mcp.conftest import EXPECTED_TOOL_COUNT

        assert len(mcp._tool_manager._tools) == EXPECTED_TOOL_COUNT

    def test_prompts_registered(self, store):
        prompt_names = set(mcp._prompt_manager._prompts.keys())
        expected = {
            "context_onboarding",
            "context_handoff",
            "context_review_decisions",
            "context_resolve_conflicts",
        }
        assert expected.issubset(prompt_names), f"Missing prompts: {expected - prompt_names}"


class TestDynamicInstructions:
    """Tests for _generate_instructions()."""

    def test_generate_instructions_with_store(self, store):
        store.set_knowledge("arch", "Hexagonal architecture")
        store.add_decision(title="Use PostgreSQL")
        result = _generate_instructions()
        assert "test-mcp-project" in result
        assert "arch" in result
        assert "1 recorded" in result
        assert "context_onboarding" in result

    def test_generate_instructions_with_skills(self, store):
        store.set_skill("deploy", "---\nname: deploy\ndescription: Deploy\n---\n\nBody.\n")
        result = _generate_instructions()
        assert "deploy" in result
        assert "1 available" in result

    def test_generate_instructions_includes_task(self, store):
        state = store.read_active_state()
        state.current_task = "Building MCP server"
        state.blockers = ["Tests failing"]
        store.write_active_state(state)
        result = _generate_instructions()
        assert "Building MCP server" in result
        assert "Tests failing" in result

    def test_generate_instructions_fallback(self, monkeypatch):
        """Without a store set, falls back to generic instructions."""
        set_store(None)
        monkeypatch.setattr("ctx.mcp.server.find_project_root", lambda: None)
        result = _generate_instructions()
        assert result == _FALLBACK_INSTRUCTIONS

    def test_generate_instructions_empty_store(self, store):
        """Initialized but empty store still includes project name."""
        result = _generate_instructions()
        assert "test-mcp-project" in result

    def test_generate_instructions_truncates_keys(self, store):
        """Instructions truncate key lists when exceeding MAX_INSTRUCTION_KEYS."""
        from ctx.mcp.server import MAX_INSTRUCTION_KEYS

        for i in range(MAX_INSTRUCTION_KEYS + 5):
            store.set_knowledge(f"k-{i:03d}", f"Content {i}")
        result = _generate_instructions()
        assert "... and 5 more" in result
        assert f"{MAX_INSTRUCTION_KEYS + 5} entries" in result


class TestLifespan:
    """Tests for the MCP server lifespan context manager."""

    @pytest.mark.anyio
    async def test_lifespan_pushes_on_shutdown(self, git_store):
        from unittest.mock import patch
        from ctx.mcp.server import _server_lifespan

        git_store.set_knowledge("push-test", "content for push")
        mock_app = type("MockApp", (), {})()

        with patch("ctx.mcp.server.GitSync") as mock_gs_cls:
            mock_gs = mock_gs_cls.return_value
            mock_gs._has_changes.return_value = True
            async with _server_lifespan(mock_app):
                pass
            mock_gs.push.assert_called_once()

    @pytest.mark.anyio
    async def test_lifespan_skips_push_no_changes(self, git_store):
        from unittest.mock import patch
        from ctx.mcp.server import _server_lifespan

        mock_app = type("MockApp", (), {})()

        with patch("ctx.mcp.server.GitSync") as mock_gs_cls:
            mock_gs = mock_gs_cls.return_value
            mock_gs._has_changes.return_value = False
            async with _server_lifespan(mock_app):
                pass
            mock_gs.push.assert_not_called()
