"""Tests for the MCP server tools, resources, and prompts."""

from __future__ import annotations

import json

import pytest

from ctx.core.store import ContextStore
from ctx.core.scope import Scope
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
)


@pytest.fixture
def store(tmp_path):
    """Create and initialize a ContextStore in a temp directory."""
    s = ContextStore(tmp_path)
    s.init(project_name="test-mcp-project")
    set_store(s)
    yield s
    set_store(None)


class TestResources:
    def test_manifest(self, store):
        result = json.loads(resource_manifest())
        assert result["project"]["name"] == "test-mcp-project"
        assert result["schema_version"] == "0.2.0"

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
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

    def test_has_at_least_12_tools(self, store):
        assert len(mcp._tool_manager._tools) >= 12

    def test_prompts_registered(self, store):
        prompt_names = set(mcp._prompt_manager._prompts.keys())
        expected = {"context_onboarding", "context_handoff", "context_review_decisions"}
        assert expected.issubset(prompt_names), f"Missing prompts: {expected - prompt_names}"
