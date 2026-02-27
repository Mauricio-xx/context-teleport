"""Tests for MCP server convention tools, resources, instructions, onboarding, scope."""

from __future__ import annotations

import json

import pytest

from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.mcp.server import (
    _generate_instructions,
    set_store,
    context_add_convention,
    context_get_convention,
    context_list_conventions,
    context_rm_convention,
    context_get_scope,
    context_set_scope,
    resource_conventions,
    resource_convention_item,
    resource_summary,
    context_onboarding,
)


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="test-conventions")
    set_store(s)
    yield s
    set_store(None)


class TestConventionTools:
    def test_add_convention(self, store):
        result = json.loads(context_add_convention("git", "Use feature branches."))
        assert result["status"] == "ok"
        assert result["key"] == "git"
        entry = store.get_convention("git")
        assert entry is not None
        assert entry.content == "Use feature branches."

    def test_get_convention(self, store):
        store.set_convention("git", "Use branches.")
        result = json.loads(context_get_convention("git"))
        assert result["key"] == "git"
        assert result["content"] == "Use branches."

    def test_get_convention_missing(self, store):
        result = json.loads(context_get_convention("missing"))
        assert "error" in result

    def test_list_conventions_empty(self, store):
        result = json.loads(context_list_conventions())
        assert result == []

    def test_list_conventions(self, store):
        store.set_convention("git", "branches")
        store.set_convention("env", "no sudo")
        result = json.loads(context_list_conventions())
        assert len(result) == 2
        keys = {r["key"] for r in result}
        assert keys == {"git", "env"}

    def test_rm_convention(self, store):
        store.set_convention("git", "content")
        result = json.loads(context_rm_convention("git"))
        assert result["status"] == "removed"
        assert store.get_convention("git") is None

    def test_rm_convention_missing(self, store):
        result = json.loads(context_rm_convention("missing"))
        assert result["status"] == "not_found"

    def test_add_convention_with_scope(self, store):
        result = json.loads(context_add_convention("secret", "hidden", scope="private"))
        assert result["status"] == "ok"
        assert store.get_convention_scope("secret") == Scope.private


class TestConventionResources:
    def test_resource_conventions_list(self, store):
        store.set_convention("git", "branches")
        result = json.loads(resource_conventions())
        assert len(result) == 1
        assert result[0]["key"] == "git"
        assert result[0]["scope"] == "public"

    def test_resource_convention_item(self, store):
        store.set_convention("git", "Use feature branches.")
        result = json.loads(resource_convention_item("git"))
        assert result["key"] == "git"
        assert "feature branches" in result["content"]

    def test_resource_convention_item_missing(self, store):
        result = json.loads(resource_convention_item("missing"))
        assert "error" in result


class TestConventionScope:
    def test_get_scope(self, store):
        store.set_convention("git", "content", scope=Scope.private)
        result = json.loads(context_get_scope("convention", "git"))
        assert result["scope"] == "private"

    def test_get_scope_missing(self, store):
        result = json.loads(context_get_scope("convention", "missing"))
        assert "error" in result

    def test_set_scope(self, store):
        store.set_convention("git", "content")
        result = json.loads(context_set_scope("convention", "git", "ephemeral"))
        assert result["status"] == "ok"
        assert store.get_convention_scope("git") == Scope.ephemeral

    def test_set_scope_missing(self, store):
        result = json.loads(context_set_scope("convention", "missing", "private"))
        assert "error" in result


class TestConventionInstructions:
    def test_instructions_include_conventions(self, store):
        store.set_convention("git", "use feature branches")
        text = _generate_instructions()
        assert "conventions" in text.lower()
        assert "git" in text

    def test_instructions_no_conventions(self, store):
        text = _generate_instructions()
        # Should not list "Team conventions" line if none exist
        assert "conventions (" not in text.lower()


class TestConventionOnboarding:
    def test_onboarding_includes_conventions(self, store):
        store.set_convention("git", "Always use feature branches.")
        text = context_onboarding()
        assert "## Team Conventions" in text
        assert "### git" in text
        assert "feature branches" in text

    def test_onboarding_conventions_before_knowledge(self, store):
        store.set_convention("git", "Use branches.")
        store.set_knowledge("arch", "Hexagonal")
        text = context_onboarding()
        conv_idx = text.index("## Team Conventions")
        know_idx = text.index("## Knowledge Base")
        assert conv_idx < know_idx

    def test_onboarding_no_conventions(self, store):
        store.set_knowledge("arch", "Hexagonal")
        text = context_onboarding()
        assert "Team Conventions" not in text
