"""Tests for the MCP server tools, resources, and prompts."""

from __future__ import annotations

import json

import git
import pytest

from ctx.core.conflicts import ConflictEntry, ConflictReport
from ctx.core.store import ContextStore
from ctx.core.scope import Scope
from ctx.sync.git_sync import GitSync
from ctx.utils.paths import STORE_DIR
from ctx.mcp.server import (
    mcp,
    set_store,
    context_search,
    context_add_knowledge,
    context_remove_knowledge,
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


class TestResources:
    def test_manifest(self, store):
        result = json.loads(resource_manifest())
        assert result["project"]["name"] == "test-mcp-project"
        assert result["schema_version"] == "0.3.0"

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

    def test_has_at_least_15_tools(self, store):
        assert len(mcp._tool_manager._tools) >= 15

    def test_prompts_registered(self, store):
        prompt_names = set(mcp._prompt_manager._prompts.keys())
        expected = {
            "context_onboarding",
            "context_handoff",
            "context_review_decisions",
            "context_resolve_conflicts",
        }
        assert expected.issubset(prompt_names), f"Missing prompts: {expected - prompt_names}"
